"""
Router de Operacoes — CRUD, upload, processamento, reprocessamento, finalizacao, envio.

Endpoints:
  POST   /operacoes                      — Criar operacao
  PATCH  /operacoes/{id}                 — Atualizar operacao (FIDC, numero)
  GET    /operacoes                      — Listar (paginado)
  GET    /operacoes/dashboard/stats      — KPIs agregados
  GET    /operacoes/dashboard/valores   — Valores agregados por periodo
  GET    /operacoes/{id}                 — Detalhes com boletos + XMLs
  DELETE /operacoes/{id}                 — Excluir operacao e dados relacionados
  POST   /operacoes/{id}/boletos/upload  — Upload PDFs (multipart + auto-split)
  POST   /operacoes/{id}/xmls/upload     — Upload XMLs (batch)
  POST   /operacoes/{id}/processar       — Extracao + renomeacao + validacao 5 camadas
  POST   /operacoes/{id}/reprocessar     — Reprocessar boletos rejeitados
  POST   /operacoes/{id}/finalizar       — Finalizar operacao + gerar relatorios
  POST   /operacoes/{id}/cancelar        — Cancelar operacao
  POST   /operacoes/{id}/enviar          — Enviar emails via SMTP (preview/automatico)
  GET    /operacoes/{id}/envios          — Listar envios da operacao
  POST   /operacoes/{id}/envios/{eid}/confirmar — Confirmar envio de rascunho SMTP
  POST   /operacoes/{id}/envios/confirmar-todos — Confirmar todos os rascunhos SMTP
  PATCH  /operacoes/{id}/xmls/{xml_id}/emails    — Editar emails de um XML
  PATCH  /operacoes/{id}/envios/{eid}/status     — Marcar envio como enviado manualmente
  GET    /operacoes/{id}/relatorio       — Download de relatorio (TXT/JSON)
  GET    /operacoes/{id}/preview-envio            — Preview agrupamento de emails
  GET    /operacoes/{id}/boletos/{bid}/arquivo   — Download/preview arquivo boleto PDF
  GET    /operacoes/{id}/xmls/{xid}/arquivo      — Download/preview arquivo XML
"""

import io
import logging
import shutil
import uuid
import zipfile
from datetime import date as date_type, datetime, timedelta, timezone
from pathlib import Path

import pdfplumber
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.extractors import (
    DadosBoleto,
    gerar_nome_arquivo,
    get_extractor_by_name,
    parse_xml_nfe,
    validar_5_camadas,
)
from app.extractors.xml_parser import DadosXmlNfe
from app.models.boleto import Boleto
from app.models.fidc import Fidc
from app.models.operacao import Operacao
from app.models.usuario import Usuario
from app.models.xml_nfe import XmlNfe
from app.models.audit_log import AuditLog
from app.models.envio import Envio
from app.schemas.operacao import (
    BoletoCompleto,
    DashboardStats,
    EnvioDetalhe,
    EnvioRequest,
    EnvioResponse,
    EnvioResultado,
    EnvioStatusUpdate,
    OperacaoCreate,
    OperacaoDetalhada,
    OperacaoUpdate,
    OperacaoFinalizada,
    OperacaoResponse,
    OperacoesPaginadas,
    ValorLiquidoUpdate,
    ValoresAgregadoItem,
    ValoresAgregadoResponse,
    AtividadeItem,
    AtividadeResponse,
    PreviewEnvioGrupo,
    PreviewEnvioResponse,
    ResultadoProcessamento,
    UploadBoletosResponse,
    UploadXmlsResponse,
    XmlEmailsUpdate,
    XmlResumo,
)
from app.schemas.fidc import FidcResponse
from app.security import get_current_user
from app.services.audit import registrar_audit
from app.services.pdf_splitter import split_pdf
from app.models.email_layout import EmailLayout
from app.services.email_grouper import EmailGroup, agrupar_boletos_para_envio
from app.services.smtp_mailer import SMTPMailer
from app.services.report_generator import (
    gerar_relatorio_aprovados_txt,
    gerar_relatorio_erros_txt,
    gerar_relatorio_json,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operacoes", tags=["operacoes"])

ACAO_LABELS: dict[str, str] = {
    "login": "Realizou login",
    "criar_operacao": "Criou a operacao",
    "atualizar_valor_liquido": "Atualizou valor liquido",
    "processar_operacao": "Processou boletos",
    "reprocessar_operacao": "Reprocessou boletos rejeitados",
    "finalizar_operacao": "Finalizou a operacao",
    "cancelar_operacao": "Cancelou a operacao",
    "enviar_operacao": "Enviou emails",
    "confirmar_envio_smtp": "Confirmou envio de email",
    "confirmar_todos_envios_smtp": "Confirmou todos os envios",
    "envio_status_manual": "Atualizou status do envio",
}


# ── Helpers ───────────────────────────────────────────────────


def _storage_path() -> Path:
    return Path(settings.STORAGE_DIR)


def _operacao_dir(operacao_id: uuid.UUID) -> Path:
    base = _storage_path() / "uploads" / str(operacao_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


async def _get_operacao(op_id: str, db: AsyncSession) -> Operacao:
    result = await db.execute(select(Operacao).where(Operacao.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operacao nao encontrada")
    return op


async def _get_fidc(fidc_id: uuid.UUID, db: AsyncSession) -> Fidc:
    result = await db.execute(select(Fidc).where(Fidc.id == fidc_id))
    fidc = result.scalar_one_or_none()
    if not fidc:
        raise HTTPException(status_code=404, detail="FIDC nao encontrado")
    return fidc


# ── POST /operacoes ──────────────────────────────────────────


@router.post("", response_model=OperacaoResponse, status_code=201)
async def create_operacao(
    body: OperacaoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    fidc = await _get_fidc(body.fidc_id, db)

    # Gera número automático sequencial se não fornecido
    numero = body.numero
    if not numero:
        max_result = await db.execute(
            select(func.max(Operacao.numero))
            .where(Operacao.numero.like("OP-%"))
        )
        max_numero = max_result.scalar()
        if max_numero:
            try:
                seq = int(max_numero.replace("OP-", "")) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        numero = f"OP-{seq:04d}"

    op = Operacao(
        numero=numero,
        fidc_id=fidc.id,
        usuario_id=current_user.id,
    )
    db.add(op)
    await registrar_audit(
        db, acao="criar_operacao", operacao_id=op.id,
        usuario_id=current_user.id, entidade="operacao",
        detalhes={"numero": numero, "fidc": fidc.nome},
    )
    await db.commit()
    await db.refresh(op)
    resp = OperacaoResponse.model_validate(op)
    resp.fidc_nome = fidc.nome
    return resp


# ── GET /operacoes ───────────────────────────────────────────


@router.get("", response_model=OperacoesPaginadas)
async def list_operacoes(
    fidc_id: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    query = select(Operacao)
    count_query = select(func.count()).select_from(Operacao)

    if fidc_id:
        query = query.where(Operacao.fidc_id == fidc_id)
        count_query = count_query.where(Operacao.fidc_id == fidc_id)
    if status_filter:
        query = query.where(Operacao.status == status_filter)
        count_query = count_query.where(Operacao.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Operacao.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    ops = result.scalars().all()

    # Resolver fidc_nome para cada operacao
    fidc_ids = list({o.fidc_id for o in ops})
    fidcs_result = await db.execute(select(Fidc).where(Fidc.id.in_(fidc_ids)))
    fidcs_map = {f.id: f.nome for f in fidcs_result.scalars().all()}

    # Resolver usuario_nome (criador) para cada operacao
    usuario_ids = list({o.usuario_id for o in ops})
    if usuario_ids:
        usuarios_result = await db.execute(select(Usuario).where(Usuario.id.in_(usuario_ids)))
        usuarios_map = {u.id: u.nome for u in usuarios_result.scalars().all()}
    else:
        usuarios_map = {}

    items = []
    for o in ops:
        resp = OperacaoResponse.model_validate(o)
        resp.fidc_nome = fidcs_map.get(o.fidc_id)
        resp.usuario_nome = usuarios_map.get(o.usuario_id)
        items.append(resp)

    return OperacoesPaginadas(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ── GET /operacoes/dashboard/stats ─────────────────────────


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """KPIs agregados de todas as operacoes."""
    # Totais
    count_result = await db.execute(select(func.count()).select_from(Operacao))
    total_ops = count_result.scalar() or 0

    sums_result = await db.execute(
        select(
            func.coalesce(func.sum(Operacao.total_boletos), 0),
            func.coalesce(func.sum(Operacao.total_aprovados), 0),
            func.coalesce(func.sum(Operacao.total_rejeitados), 0),
        )
    )
    row = sums_result.one()
    total_boletos = int(row[0])
    total_aprovados = int(row[1])
    total_rejeitados = int(row[2])

    taxa = (total_aprovados / total_boletos * 100) if total_boletos > 0 else 0.0

    # 5 operacoes mais recentes
    recentes_result = await db.execute(
        select(Operacao).order_by(Operacao.created_at.desc()).limit(5)
    )
    recentes = recentes_result.scalars().all()

    fidc_ids = list({o.fidc_id for o in recentes})
    if fidc_ids:
        fidcs_result = await db.execute(select(Fidc).where(Fidc.id.in_(fidc_ids)))
        fidcs_map = {f.id: f.nome for f in fidcs_result.scalars().all()}
    else:
        fidcs_map = {}

    usuario_ids = list({o.usuario_id for o in recentes})
    if usuario_ids:
        usuarios_result = await db.execute(select(Usuario).where(Usuario.id.in_(usuario_ids)))
        usuarios_map = {u.id: u.nome for u in usuarios_result.scalars().all()}
    else:
        usuarios_map = {}

    recentes_resp = []
    for o in recentes:
        resp = OperacaoResponse.model_validate(o)
        resp.fidc_nome = fidcs_map.get(o.fidc_id)
        resp.usuario_nome = usuarios_map.get(o.usuario_id)
        recentes_resp.append(resp)

    return DashboardStats(
        total_operacoes=total_ops,
        total_boletos=total_boletos,
        total_aprovados=total_aprovados,
        total_rejeitados=total_rejeitados,
        taxa_sucesso_global=round(taxa, 2),
        operacoes_recentes=recentes_resp,
    )


# ── GET /operacoes/dashboard/valores ──────────────────────


@router.get("/dashboard/valores", response_model=ValoresAgregadoResponse)
async def dashboard_valores(
    data_inicio: date_type | None = Query(None, description="Data inicio (YYYY-MM-DD)"),
    data_fim: date_type | None = Query(None, description="Data fim (YYYY-MM-DD)"),
    agrupamento: str = Query("mes", description="dia | semana | mes"),
    fidc_id: str | None = Query(None, description="Filtro por FIDC"),
    status_filter: str | None = Query(None, description="Filtro por status"),
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Valores bruto/liquido agregados por periodo (dia, semana, mes)."""
    if not data_fim:
        data_fim = date_type.today()
    if not data_inicio:
        data_inicio = data_fim - timedelta(days=180)

    trunc_map = {"dia": "day", "semana": "week", "mes": "month"}
    pg_trunc = trunc_map.get(agrupamento)
    if not pg_trunc:
        raise HTTPException(
            status_code=400,
            detail="agrupamento deve ser: dia, semana ou mes",
        )

    dt_inicio = datetime.combine(data_inicio, datetime.min.time())
    dt_fim = datetime.combine(data_fim, datetime.max.time())

    periodo_col = func.date_trunc(pg_trunc, Operacao.created_at).label("periodo")

    query = (
        select(
            periodo_col,
            func.coalesce(func.sum(Operacao.valor_bruto), 0.0).label("valor_bruto"),
            func.coalesce(func.sum(Operacao.valor_liquido), 0.0).label("valor_liquido"),
            func.count(Operacao.id).label("count"),
        )
        .where(Operacao.created_at >= dt_inicio)
        .where(Operacao.created_at <= dt_fim)
    )

    if fidc_id:
        query = query.where(Operacao.fidc_id == fidc_id)
    if status_filter:
        query = query.where(Operacao.status == status_filter)

    query = query.group_by(periodo_col).order_by(periodo_col)

    result = await db.execute(query)
    rows = result.all()

    items = []
    total_bruto = 0.0
    total_liquido = 0.0
    total_ops = 0

    for row in rows:
        periodo_dt = row.periodo
        vb = float(row.valor_bruto)
        vl = float(row.valor_liquido)
        cnt = int(row.count)

        if agrupamento == "mes":
            periodo_str = periodo_dt.strftime("%Y-%m")
            periodo_label = periodo_dt.strftime("%b/%Y").capitalize()
        elif agrupamento == "semana":
            iso_cal = periodo_dt.isocalendar()
            periodo_str = f"{iso_cal.year}-W{iso_cal.week:02d}"
            periodo_label = f"Sem {iso_cal.week:02d}"
        else:
            periodo_str = periodo_dt.strftime("%Y-%m-%d")
            periodo_label = periodo_dt.strftime("%d/%m/%Y")

        items.append(ValoresAgregadoItem(
            periodo=periodo_str,
            periodo_label=periodo_label,
            valor_bruto=round(vb, 2),
            valor_liquido=round(vl, 2),
            count=cnt,
        ))
        total_bruto += vb
        total_liquido += vl
        total_ops += cnt

    return ValoresAgregadoResponse(
        items=items,
        total_bruto=round(total_bruto, 2),
        total_liquido=round(total_liquido, 2),
        total_operacoes=total_ops,
    )


# ── PATCH /operacoes/{id} ───────────────────────────────────


@router.patch("/{op_id}", response_model=OperacaoResponse)
async def update_operacao(
    op_id: str,
    payload: OperacaoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Operacao).where(Operacao.id == op_id)
    )
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operacao nao encontrada")

    if payload.fidc_id is not None:
        fidc_result = await db.execute(select(Fidc).where(Fidc.id == payload.fidc_id))
        fidc = fidc_result.scalar_one_or_none()
        if not fidc:
            raise HTTPException(status_code=404, detail="FIDC nao encontrado")
        op.fidc_id = payload.fidc_id

    if payload.numero is not None:
        op.numero = payload.numero

    await db.commit()
    await db.refresh(op)

    fidc_result = await db.execute(select(Fidc).where(Fidc.id == op.fidc_id))
    fidc = fidc_result.scalar_one_or_none()

    return OperacaoResponse(
        id=op.id,
        numero=op.numero,
        fidc_id=op.fidc_id,
        fidc_nome=fidc.nome if fidc else None,
        status=op.status,
        modo_envio=op.modo_envio,
        total_boletos=op.total_boletos,
        total_aprovados=op.total_aprovados,
        total_rejeitados=op.total_rejeitados,
        taxa_sucesso=op.taxa_sucesso,
        valor_bruto=op.valor_bruto,
        valor_liquido=op.valor_liquido,
        created_at=op.created_at,
        updated_at=op.updated_at,
    )


# ── PATCH /operacoes/{op_id}/valor-liquido ──────────────────


@router.patch("/{op_id}/valor-liquido", response_model=OperacaoResponse)
async def atualizar_valor_liquido(
    op_id: str,
    body: ValorLiquidoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Atualiza o valor liquido de uma operacao."""
    op = await _get_operacao(op_id, db)

    op.valor_liquido = body.valor_liquido

    await registrar_audit(
        db, acao="atualizar_valor_liquido", operacao_id=op.id,
        usuario_id=current_user.id, entidade="operacao",
        detalhes={"valor_liquido": body.valor_liquido},
    )
    await db.commit()
    await db.refresh(op)

    fidc = await _get_fidc(op.fidc_id, db)
    resp = OperacaoResponse.model_validate(op)
    resp.fidc_nome = fidc.nome
    return resp


# ── GET /operacoes/{op_id}/boletos/{boleto_id}/arquivo ──────


@router.get("/{op_id}/boletos/{boleto_id}/arquivo")
async def download_boleto_arquivo(
    op_id: str,
    boleto_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Serve o arquivo PDF de um boleto."""
    op = await _get_operacao(op_id, db)
    result = await db.execute(
        select(Boleto).where(Boleto.id == boleto_id, Boleto.operacao_id == op.id)
    )
    boleto = result.scalar_one_or_none()
    if not boleto or not boleto.arquivo_path:
        raise HTTPException(status_code=404, detail="Arquivo do boleto nao encontrado")

    file_path = Path(boleto.arquivo_path)
    # Fallback: se o path original nao existe mas o arquivo foi renomeado
    if not file_path.exists() and boleto.arquivo_renomeado:
        file_path = file_path.parent / boleto.arquivo_renomeado
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo do boleto nao encontrado no disco")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=boleto.arquivo_renomeado or boleto.arquivo_original,
    )


# ── GET /operacoes/{op_id}/xmls/{xml_id}/arquivo ───────────


@router.get("/{op_id}/xmls/{xml_id}/arquivo")
async def download_xml_arquivo(
    op_id: str,
    xml_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Serve o arquivo XML/PDF de um XML da operacao."""
    op = await _get_operacao(op_id, db)
    result = await db.execute(
        select(XmlNfe).where(XmlNfe.id == xml_id, XmlNfe.operacao_id == op.id)
    )
    xml = result.scalar_one_or_none()
    if not xml:
        raise HTTPException(status_code=404, detail="XML nao encontrado")

    file_path = _operacao_dir(op.id) / "xmls" / xml.nome_arquivo
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo XML nao encontrado no disco")

    suffix = file_path.suffix.lower()
    media_type = "text/xml" if suffix == ".xml" else "application/pdf"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=xml.nome_arquivo,
    )


# ── GET /operacoes/{op_id}/preview-envio ────────────────────


@router.get("/{op_id}/preview-envio", response_model=PreviewEnvioResponse)
async def preview_envio(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Retorna agrupamento de emails para preview, sem enviar."""
    op = await _get_operacao(op_id, db)
    fidc = await _get_fidc(op.fidc_id, db)

    # Buscar boletos aprovados
    boletos_result = await db.execute(
        select(Boleto)
        .where(Boleto.operacao_id == op.id)
        .where(Boleto.status == "aprovado")
    )
    boletos_aprovados = boletos_result.scalars().all()

    if not boletos_aprovados:
        return PreviewEnvioResponse(total_grupos=0, total_aprovados=0, grupos=[])

    # Buscar XMLs
    xmls_result = await db.execute(
        select(XmlNfe).where(XmlNfe.operacao_id == op.id)
    )
    xmls = xmls_result.scalars().all()

    # Buscar layout de email ativo
    layout_result = await db.execute(select(EmailLayout).where(EmailLayout.ativo == True))
    active_layout = layout_result.scalar_one_or_none()
    layout_dict = None
    if active_layout:
        layout_dict = {
            "saudacao": active_layout.saudacao,
            "introducao": active_layout.introducao,
            "mensagem_fechamento": active_layout.mensagem_fechamento,
            "assinatura_nome": active_layout.assinatura_nome,
        }

    # Override com textos do FIDC (se definidos)
    if layout_dict is None:
        layout_dict = {}
    if fidc.email_introducao:
        layout_dict["introducao"] = fidc.email_introducao
    if fidc.email_mensagem_fechamento:
        layout_dict["mensagem_fechamento"] = fidc.email_mensagem_fechamento
    if fidc.email_assinatura_nome:
        layout_dict["assinatura_nome"] = fidc.email_assinatura_nome

    # Agrupar por email destino
    storage_base = _storage_path() / "uploads" / str(op.id)
    grupos = agrupar_boletos_para_envio(boletos_aprovados, xmls, fidc, storage_base, email_layout=layout_dict)

    # Mapas para lookup rapido
    boletos_map = {str(b.id): b for b in boletos_aprovados}
    xmls_map = {str(x.id): x for x in xmls}

    # Mapa de NF PDFs por numero_nota (para mostrar PDF em vez de XML no preview)
    nf_pdfs_by_nota: dict[str, XmlNfe] = {}
    for x in xmls:
        if x.nome_arquivo.lower().endswith(".pdf"):
            nf_key = (x.numero_nota or "").lstrip("0") or "0"
            nf_pdfs_by_nota[nf_key] = x

    preview_grupos = []
    for grupo in grupos:
        grupo_boletos = [
            BoletoCompleto.model_validate(boletos_map[bid])
            for bid in grupo.boletos_ids
            if bid in boletos_map
        ]
        # Substituir XMLs por NF PDFs quando disponivel
        grupo_xmls = []
        seen_notas = set()
        for xid in grupo.xmls_ids:
            xml_rec = xmls_map.get(xid)
            if not xml_rec:
                continue
            nf_key = (xml_rec.numero_nota or "").lstrip("0") or "0"
            if nf_key in seen_notas:
                continue
            seen_notas.add(nf_key)
            pdf_rec = nf_pdfs_by_nota.get(nf_key)
            if pdf_rec:
                grupo_xmls.append(XmlResumo.model_validate(pdf_rec))
            else:
                grupo_xmls.append(XmlResumo.model_validate(xml_rec))
        preview_grupos.append(PreviewEnvioGrupo(
            email_para=grupo.email_para,
            email_cc=grupo.email_cc,
            assunto=grupo.assunto,
            corpo_html=grupo.corpo_html,
            boletos=grupo_boletos,
            xmls=grupo_xmls,
        ))

    return PreviewEnvioResponse(
        total_grupos=len(preview_grupos),
        total_aprovados=len(boletos_aprovados),
        grupos=preview_grupos,
    )


# ── GET /operacoes/{id}/download-arquivos ──────────────────


@router.get("/{op_id}/download-arquivos")
async def download_arquivos(
    op_id: str,
    tipo: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Baixa ZIP com todos os arquivos de um tipo (boletos, xmls, nfs)."""
    op = await _get_operacao(op_id, db)
    op_dir = _operacao_dir(op.id)

    label = op.numero or str(op.id)[:8]

    if tipo == "boletos":
        source_dir = op_dir / "boletos"
        ext_filter = ".pdf"
        zip_name = f"boletos_{label}.zip"
    elif tipo == "xmls":
        source_dir = op_dir / "xmls"
        ext_filter = ".xml"
        zip_name = f"xmls_{label}.zip"
    elif tipo == "nfs":
        source_dir = op_dir / "xmls"
        ext_filter = ".pdf"
        zip_name = f"notas_fiscais_{label}.zip"
    else:
        raise HTTPException(status_code=400, detail="tipo deve ser: boletos, xmls ou nfs")

    # Para boletos, usar registros do DB com nomes renomeados
    if tipo == "boletos":
        boletos_result = await db.execute(
            select(Boleto).where(Boleto.operacao_id == op.id)
        )
        boletos_all = boletos_result.scalars().all()
        arquivos_boleto: list[tuple[Path, str]] = []
        for b in boletos_all:
            if not b.arquivo_path:
                continue
            file_path = Path(b.arquivo_path)
            if not file_path.exists():
                continue
            zip_name_entry = b.arquivo_renomeado or file_path.name
            arquivos_boleto.append((file_path, zip_name_entry))

        if not arquivos_boleto:
            raise HTTPException(status_code=404, detail="Nenhum arquivo encontrado para download")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path, entry_name in arquivos_boleto:
                zf.write(file_path, entry_name)
    else:
        if not source_dir.exists():
            raise HTTPException(status_code=404, detail="Diretorio de arquivos nao encontrado")

        arquivos = [
            f for f in sorted(source_dir.iterdir())
            if f.is_file() and f.name.lower().endswith(ext_filter)
        ]

        if not arquivos:
            raise HTTPException(status_code=404, detail="Nenhum arquivo encontrado para download")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in arquivos:
                zf.write(f, f.name)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


# ── GET /operacoes/{id}/atividade ──────────────────────────


@router.get("/{op_id}/atividade", response_model=AtividadeResponse)
async def listar_atividade(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Lista historico de acoes (audit trail) de uma operacao."""
    await _get_operacao(op_id, db)

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.operacao_id == op_id)
        .order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()

    usuario_ids = list({log.usuario_id for log in logs if log.usuario_id})
    if usuario_ids:
        usuarios_result = await db.execute(
            select(Usuario).where(Usuario.id.in_(usuario_ids))
        )
        usuarios_map = {u.id: u.nome for u in usuarios_result.scalars().all()}
    else:
        usuarios_map = {}

    items = [
        AtividadeItem(
            id=log.id,
            acao=log.acao,
            acao_label=ACAO_LABELS.get(log.acao, log.acao),
            usuario_nome=usuarios_map.get(log.usuario_id) if log.usuario_id else None,
            detalhes=log.detalhes,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AtividadeResponse(items=items, total=len(items))


# ── GET /operacoes/{id} ─────────────────────────────────────


@router.get("/{op_id}", response_model=OperacaoDetalhada)
async def get_operacao_detail(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    op = await _get_operacao(op_id, db)
    fidc = await _get_fidc(op.fidc_id, db)

    boletos_result = await db.execute(
        select(Boleto).where(Boleto.operacao_id == op.id).order_by(Boleto.created_at)
    )
    boletos = boletos_result.scalars().all()

    xmls_result = await db.execute(
        select(XmlNfe).where(XmlNfe.operacao_id == op.id).order_by(XmlNfe.created_at)
    )
    xmls = xmls_result.scalars().all()

    return OperacaoDetalhada(
        id=op.id,
        numero=op.numero,
        fidc=FidcResponse.model_validate(fidc),
        status=op.status,
        modo_envio=op.modo_envio,
        total_boletos=op.total_boletos,
        total_aprovados=op.total_aprovados,
        total_rejeitados=op.total_rejeitados,
        taxa_sucesso=op.taxa_sucesso,
        valor_bruto=op.valor_bruto,
        valor_liquido=op.valor_liquido,
        created_at=op.created_at,
        boletos=[BoletoCompleto.model_validate(b) for b in boletos],
        xmls=[XmlResumo.model_validate(x) for x in xmls],
    )


# ── POST /operacoes/{id}/boletos/upload ──────────────────────


@router.post("/{op_id}/boletos/upload", response_model=UploadBoletosResponse)
async def upload_boletos(
    op_id: str,
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    op = await _get_operacao(op_id, db)
    fidc = await _get_fidc(op.fidc_id, db)

    op_dir = _operacao_dir(op.id)
    boletos_dir = op_dir / "boletos"
    split_dir = op_dir / "boletos_split"
    boletos_dir.mkdir(parents=True, exist_ok=True)
    split_dir.mkdir(parents=True, exist_ok=True)

    # Obter extrator pelo FIDC para extracao antecipada
    extrator = get_extractor_by_name(fidc.nome)

    total_paginas = 0
    boletos_criados: list[BoletoCompleto] = []

    for file in files:
        # Validacao: apenas PDF
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Formato invalido: {file.filename}. Apenas arquivos PDF sao aceitos.",
            )

        # Verificar duplicata: arquivo original ja existe no filesystem
        orig_path = boletos_dir / file.filename
        if orig_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo duplicado: {file.filename} ja foi enviado nesta operacao.",
            )

        # Salva arquivo original
        content = await file.read()
        orig_path.write_bytes(content)

        # Auto-split
        split_files = split_pdf(orig_path, split_dir)
        total_paginas += len(split_files)

        # Cria registro no banco para cada pagina + extracao antecipada
        for sf in split_files:
            boleto = Boleto(
                operacao_id=op.id,
                arquivo_original=sf.name,
                arquivo_path=str(sf),
            )

            # Extracao antecipada: extrair dados do PDF
            try:
                texto = _extrair_texto_pdf(str(sf))
                dados_boleto = extrator.extrair(texto, sf.name)
                nome_renomeado = gerar_nome_arquivo(dados_boleto)

                boleto.pagador = dados_boleto.pagador
                boleto.cnpj = dados_boleto.cnpj
                boleto.numero_nota = dados_boleto.numero_nota
                boleto.vencimento = dados_boleto.vencimento
                boleto.vencimento_date = _parse_vencimento_date(dados_boleto.vencimento_completo)
                boleto.valor = dados_boleto.valor
                boleto.valor_formatado = dados_boleto.valor_formatado
                boleto.fidc_detectada = dados_boleto.fidc_detectada
                boleto.arquivo_renomeado = nome_renomeado
            except Exception as exc:
                logger.warning("Extracao antecipada falhou para %s: %s", sf.name, exc)

            db.add(boleto)
            await db.flush()
            boletos_criados.append(BoletoCompleto.model_validate(boleto))

    # Atualiza total na operacao
    op.total_boletos = len(boletos_criados)
    await db.commit()

    return UploadBoletosResponse(
        total_paginas=total_paginas,
        boletos_criados=len(boletos_criados),
        boletos=boletos_criados,
    )


# ── POST /operacoes/{id}/xmls/upload ────────────────────────


@router.post("/{op_id}/xmls/upload", response_model=UploadXmlsResponse)
async def upload_xmls(
    op_id: str,
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    op = await _get_operacao(op_id, db)

    # Buscar numero_nota existentes (normalizados) para dedup XML vs PDF
    existing_notas = await db.execute(
        select(XmlNfe.numero_nota).where(XmlNfe.operacao_id == op.id)
    )
    existing_notas_set = {(row[0] or "").lstrip("0") or "0" for row in existing_notas.all()}

    op_dir = _operacao_dir(op.id)
    xmls_dir = op_dir / "xmls"
    xmls_dir.mkdir(parents=True, exist_ok=True)

    xmls_result: list[XmlResumo] = []
    validos = 0
    invalidos = 0

    # Ordenar: XMLs primeiro, PDFs depois (XMLs tem dados completos, PDFs sao skip se duplicado)
    files_sorted = sorted(files, key=lambda f: 1 if (f.filename or "").lower().endswith(".pdf") else 0)
    logger.info("UPLOAD_XMLS: %d arquivos recebidos, ordem: %s", len(files_sorted), [f.filename for f in files_sorted])

    for file in files_sorted:
        # Validacao: XML ou PDF
        if not file.filename or not file.filename.lower().endswith((".xml", ".pdf")):
            raise HTTPException(
                status_code=400,
                detail=f"Formato invalido: {file.filename}. Apenas arquivos XML ou PDF sao aceitos.",
            )

        # Verificar duplicata: arquivo ja existe no filesystem
        nf_path = xmls_dir / file.filename
        if nf_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo duplicado: {file.filename} ja foi enviado nesta operacao.",
            )
        content = await file.read()
        nf_path.write_bytes(content)

        is_pdf = file.filename.lower().endswith(".pdf")

        if is_pdf:
            # PDF de nota fiscal — salvar como anexo sem parse
            # Extrair numero da nota do nome do arquivo (ex: 3-0318865.pdf → 318865)
            stem = nf_path.stem
            raw = stem.split("-")[-1] if "-" in stem else stem
            numero_nota = raw.lstrip("0") or "0"

            # Se ja existe XML com mesmo numero_nota, copiar dados para enriquecer o PDF
            enriched: dict = {}
            if numero_nota in existing_notas_set:
                existing_xml = await db.execute(
                    select(XmlNfe).where(
                        XmlNfe.operacao_id == op.id,
                        XmlNfe.numero_nota == numero_nota,
                        XmlNfe.nome_arquivo.ilike("%.xml"),
                    )
                )
                xml_src = existing_xml.scalars().first()
                if xml_src:
                    enriched = {
                        "cnpj": xml_src.cnpj,
                        "nome_destinatario": xml_src.nome_destinatario,
                        "valor_total": xml_src.valor_total,
                        "emails": xml_src.emails or [],
                        "emails_invalidos": xml_src.emails_invalidos or [],
                    }

            xml_record = XmlNfe(
                operacao_id=op.id,
                nome_arquivo=file.filename,
                numero_nota=numero_nota,
                cnpj=enriched.get("cnpj"),
                nome_destinatario=enriched.get("nome_destinatario"),
                valor_total=enriched.get("valor_total"),
                emails=enriched.get("emails", []),
                emails_invalidos=enriched.get("emails_invalidos", []),
                duplicatas=[],
                xml_valido=True,
                dados_raw={},
            )
            db.add(xml_record)
            await db.flush()
            existing_notas_set.add(numero_nota)
            validos += 1
        else:
            # Parse XML NFe
            dados = parse_xml_nfe(nf_path)
            nf_normalizado = (dados.numero_nota or "").lstrip("0") or "0"

            # Pular se ja existe registro com mesmo numero_nota
            if nf_normalizado in existing_notas_set:
                continue

            xml_record = XmlNfe(
                operacao_id=op.id,
                nome_arquivo=file.filename,
                numero_nota=dados.numero_nota,
                cnpj=dados.cnpj,
                nome_destinatario=dados.nome_destinatario,
                valor_total=dados.valor_total,
                emails=dados.emails,
                emails_invalidos=dados.emails_invalidos,
                duplicatas=dados.duplicatas,
                xml_valido=dados.xml_valido,
                dados_raw=dados.dados_raw,
            )
            db.add(xml_record)
            await db.flush()
            existing_notas_set.add(nf_normalizado)

            if dados.xml_valido:
                validos += 1
            else:
                invalidos += 1

        xmls_result.append(XmlResumo.model_validate(xml_record))

    await db.commit()

    return UploadXmlsResponse(
        total_xmls=len(xmls_result),
        validos=validos,
        invalidos=invalidos,
        xmls=xmls_result,
    )


# ── POST /operacoes/{id}/processar ──────────────────────────


@router.post("/{op_id}/processar", response_model=ResultadoProcessamento)
async def processar_operacao(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    op = await _get_operacao(op_id, db)
    fidc = await _get_fidc(op.fidc_id, db)

    # Carregar XMLs da operação → mapa por número da nota
    xmls_result = await db.execute(select(XmlNfe).where(XmlNfe.operacao_id == op.id))
    xmls = xmls_result.scalars().all()

    mapa_xmls: dict[str, tuple[XmlNfe, DadosXmlNfe]] = {}
    for xml_record in xmls:
        nf = xml_record.numero_nota.lstrip("0")
        # Priorizar XMLs sobre PDFs (PDFs de NF sao apenas para exibicao)
        if nf in mapa_xmls and xml_record.nome_arquivo.lower().endswith(".pdf"):
            continue
        dados_xml = DadosXmlNfe(
            xml_valido=xml_record.xml_valido,
            numero_nota=xml_record.numero_nota,
            cnpj=xml_record.cnpj or "",
            nome_destinatario=xml_record.nome_destinatario or "",
            valor_total=xml_record.valor_total or 0.0,
            emails=xml_record.emails or [],
            emails_invalidos=xml_record.emails_invalidos or [],
            duplicatas=xml_record.duplicatas or [],
        )
        mapa_xmls[nf] = (xml_record, dados_xml)

    # Obter extrator pelo FIDC
    extrator = get_extractor_by_name(fidc.nome)

    # Carregar boletos pendentes
    boletos_result = await db.execute(
        select(Boleto)
        .where(Boleto.operacao_id == op.id)
        .where(Boleto.status == "pendente")
    )
    boletos = boletos_result.scalars().all()

    aprovados = 0
    rejeitados = 0
    boletos_processados: list[BoletoCompleto] = []

    # Debug: pasta para salvar texto bruto extraido
    debug_dir = _operacao_dir(op.id) / "_debug_texto"
    debug_dir.mkdir(exist_ok=True)

    for boleto in boletos:
        # 1. Extrair texto do PDF
        texto = _extrair_texto_pdf(boleto.arquivo_path)

        # DEBUG: salvar texto bruto para analise
        try:
            stem = Path(boleto.arquivo_original).stem if boleto.arquivo_original else "unknown"
            (debug_dir / f"{stem}.txt").write_text(texto, encoding="utf-8")
        except Exception:
            pass  # nao falhar por causa do debug

        # 2. Extrair dados com o extrator do FIDC
        dados_boleto = extrator.extrair(texto, boleto.arquivo_original)

        # DEBUG: log dos dados extraidos
        logger.info(
            "EXTRACAO [%s]: pagador=%s | valor=%s | nf=%s | venc=%s | cnpj=%s",
            boleto.arquivo_original,
            dados_boleto.pagador,
            dados_boleto.valor_formatado,
            dados_boleto.numero_nota,
            dados_boleto.vencimento,
            dados_boleto.cnpj,
        )

        # 3. Encontrar XML correspondente
        nf_key = (dados_boleto.numero_nota or "").lstrip("0")
        xml_pair = mapa_xmls.get(nf_key)
        xml_record = xml_pair[0] if xml_pair else None
        dados_xml = xml_pair[1] if xml_pair else None

        # 4. Validação 5 camadas
        resultado = validar_5_camadas(dados_boleto, dados_xml)

        # 5. Gerar nome renomeado
        nome_renomeado = gerar_nome_arquivo(dados_boleto)

        # 6. Atualizar registro do boleto
        boleto.pagador = dados_boleto.pagador
        boleto.cnpj = dados_boleto.cnpj
        boleto.numero_nota = dados_boleto.numero_nota
        boleto.vencimento = dados_boleto.vencimento
        boleto.vencimento_date = _parse_vencimento_date(dados_boleto.vencimento_completo)
        boleto.valor = dados_boleto.valor
        boleto.valor_formatado = dados_boleto.valor_formatado
        boleto.fidc_detectada = dados_boleto.fidc_detectada
        boleto.arquivo_renomeado = nome_renomeado
        boleto.juros_detectado = resultado.juros_detectado

        # Validações por camada
        camadas = {c.camada: c for c in resultado.camadas}
        boleto.validacao_camada1 = _camada_to_dict(camadas.get(1))
        boleto.validacao_camada2 = _camada_to_dict(camadas.get(2))
        boleto.validacao_camada3 = _camada_to_dict(camadas.get(3))
        boleto.validacao_camada4 = _camada_to_dict(camadas.get(4))
        boleto.validacao_camada5 = _camada_to_dict(camadas.get(5))

        if resultado.aprovado:
            boleto.status = "aprovado"
            aprovados += 1
        else:
            boleto.status = "rejeitado"
            boleto.motivo_rejeicao = resultado.motivo_rejeicao
            rejeitados += 1

        # Vincular ao XML
        if xml_record:
            boleto.xml_nfe_id = xml_record.id

        # Renomear arquivo fisicamente e atualizar path no banco
        if boleto.arquivo_path and resultado.aprovado:
            _renomear_arquivo(Path(boleto.arquivo_path), nome_renomeado)
            boleto.arquivo_path = str(Path(boleto.arquivo_path).parent / nome_renomeado)

        boletos_processados.append(BoletoCompleto.model_validate(boleto))

    # Atualizar totais da operacao
    total = aprovados + rejeitados
    op.total_boletos = total
    op.total_aprovados = aprovados
    op.total_rejeitados = rejeitados
    op.taxa_sucesso = (aprovados / total * 100) if total > 0 else 0.0

    # Computar valor bruto (soma dos boletos aprovados)
    valor_bruto_total = sum(
        b.valor for b in boletos
        if b.status == "aprovado" and b.valor is not None
    )
    op.valor_bruto = valor_bruto_total if valor_bruto_total > 0 else None

    await registrar_audit(
        db, acao="processar_operacao", operacao_id=op.id,
        usuario_id=_current_user.id, entidade="operacao",
        detalhes={"total": total, "aprovados": aprovados, "rejeitados": rejeitados},
    )
    await db.commit()

    return ResultadoProcessamento(
        total=total,
        aprovados=aprovados,
        rejeitados=rejeitados,
        taxa_sucesso=op.taxa_sucesso,
        valor_bruto=op.valor_bruto,
        boletos=boletos_processados,
    )


# ── POST /operacoes/{id}/reprocessar ─────────────────────────


@router.post("/{op_id}/reprocessar", response_model=ResultadoProcessamento)
async def reprocessar_operacao(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Reprocessa apenas boletos com status 'rejeitado'."""
    op = await _get_operacao(op_id, db)

    if op.status != "em_processamento":
        raise HTTPException(
            status_code=400,
            detail="Apenas operacoes em processamento podem ser reprocessadas",
        )

    fidc = await _get_fidc(op.fidc_id, db)

    # Recarregar mapa de XMLs
    xmls_result = await db.execute(select(XmlNfe).where(XmlNfe.operacao_id == op.id))
    xmls = xmls_result.scalars().all()

    mapa_xmls: dict[str, tuple[XmlNfe, DadosXmlNfe]] = {}
    for xml_record in xmls:
        nf = xml_record.numero_nota.lstrip("0")
        # Priorizar XMLs sobre PDFs (PDFs de NF sao apenas para exibicao)
        if nf in mapa_xmls and xml_record.nome_arquivo.lower().endswith(".pdf"):
            continue
        dados_xml = DadosXmlNfe(
            xml_valido=xml_record.xml_valido,
            numero_nota=xml_record.numero_nota,
            cnpj=xml_record.cnpj or "",
            nome_destinatario=xml_record.nome_destinatario or "",
            valor_total=xml_record.valor_total or 0.0,
            emails=xml_record.emails or [],
            emails_invalidos=xml_record.emails_invalidos or [],
            duplicatas=xml_record.duplicatas or [],
        )
        mapa_xmls[nf] = (xml_record, dados_xml)

    extrator = get_extractor_by_name(fidc.nome)

    # Buscar APENAS boletos rejeitados
    boletos_result = await db.execute(
        select(Boleto)
        .where(Boleto.operacao_id == op.id)
        .where(Boleto.status == "rejeitado")
    )
    boletos_rejeitados = boletos_result.scalars().all()

    if not boletos_rejeitados:
        raise HTTPException(
            status_code=400,
            detail="Nenhum boleto rejeitado para reprocessar",
        )

    novos_aprovados = 0
    ainda_rejeitados = 0
    boletos_processados: list[BoletoCompleto] = []

    # Debug: pasta para salvar texto bruto extraido
    debug_dir = _operacao_dir(op.id) / "_debug_texto"
    debug_dir.mkdir(exist_ok=True)

    for boleto in boletos_rejeitados:
        texto = _extrair_texto_pdf(boleto.arquivo_path)

        # DEBUG: salvar texto bruto para analise
        try:
            stem = Path(boleto.arquivo_original).stem if boleto.arquivo_original else "unknown"
            (debug_dir / f"{stem}.txt").write_text(texto, encoding="utf-8")
        except Exception:
            pass

        dados_boleto = extrator.extrair(texto, boleto.arquivo_original)

        nf_key = (dados_boleto.numero_nota or "").lstrip("0")
        xml_pair = mapa_xmls.get(nf_key)
        xml_record = xml_pair[0] if xml_pair else None
        dados_xml = xml_pair[1] if xml_pair else None

        resultado = validar_5_camadas(dados_boleto, dados_xml)
        nome_renomeado = gerar_nome_arquivo(dados_boleto)

        # Atualizar dados extraidos
        boleto.pagador = dados_boleto.pagador
        boleto.cnpj = dados_boleto.cnpj
        boleto.numero_nota = dados_boleto.numero_nota
        boleto.vencimento = dados_boleto.vencimento
        boleto.vencimento_date = _parse_vencimento_date(dados_boleto.vencimento_completo)
        boleto.valor = dados_boleto.valor
        boleto.valor_formatado = dados_boleto.valor_formatado
        boleto.fidc_detectada = dados_boleto.fidc_detectada
        boleto.arquivo_renomeado = nome_renomeado
        boleto.juros_detectado = resultado.juros_detectado

        camadas = {c.camada: c for c in resultado.camadas}
        boleto.validacao_camada1 = _camada_to_dict(camadas.get(1))
        boleto.validacao_camada2 = _camada_to_dict(camadas.get(2))
        boleto.validacao_camada3 = _camada_to_dict(camadas.get(3))
        boleto.validacao_camada4 = _camada_to_dict(camadas.get(4))
        boleto.validacao_camada5 = _camada_to_dict(camadas.get(5))

        if resultado.aprovado:
            boleto.status = "aprovado"
            boleto.motivo_rejeicao = None
            novos_aprovados += 1
            if boleto.arquivo_path:
                _renomear_arquivo(Path(boleto.arquivo_path), nome_renomeado)
                boleto.arquivo_path = str(Path(boleto.arquivo_path).parent / nome_renomeado)
        else:
            boleto.status = "rejeitado"
            boleto.motivo_rejeicao = resultado.motivo_rejeicao
            ainda_rejeitados += 1

        if xml_record:
            boleto.xml_nfe_id = xml_record.id

        boletos_processados.append(BoletoCompleto.model_validate(boleto))

    # Recalcular totais da operacao (incluindo aprovados anteriores)
    all_boletos_result = await db.execute(
        select(Boleto).where(Boleto.operacao_id == op.id)
    )
    all_boletos = all_boletos_result.scalars().all()
    total_aprovados = sum(1 for b in all_boletos if b.status == "aprovado")
    total_rejeitados = sum(1 for b in all_boletos if b.status == "rejeitado")
    total = len(all_boletos)

    op.total_boletos = total
    op.total_aprovados = total_aprovados
    op.total_rejeitados = total_rejeitados
    op.taxa_sucesso = (total_aprovados / total * 100) if total > 0 else 0.0

    # Recalcular valor bruto (soma dos boletos aprovados)
    valor_bruto_total = sum(
        b.valor for b in all_boletos
        if b.status == "aprovado" and b.valor is not None
    )
    op.valor_bruto = valor_bruto_total if valor_bruto_total > 0 else None

    await registrar_audit(
        db, acao="reprocessar_operacao", operacao_id=op.id,
        usuario_id=current_user.id, entidade="operacao",
        detalhes={
            "reprocessados": len(boletos_rejeitados),
            "novos_aprovados": novos_aprovados,
            "ainda_rejeitados": ainda_rejeitados,
        },
    )
    await db.commit()

    return ResultadoProcessamento(
        total=len(boletos_rejeitados),
        aprovados=novos_aprovados,
        rejeitados=ainda_rejeitados,
        taxa_sucesso=op.taxa_sucesso,
        valor_bruto=op.valor_bruto,
        boletos=boletos_processados,
    )


# ── POST /operacoes/{id}/finalizar ───────────────────────────


@router.post("/{op_id}/finalizar", response_model=OperacaoFinalizada)
async def finalizar_operacao(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Finaliza operacao: gera relatorios e muda status para concluida."""
    op = await _get_operacao(op_id, db)

    if op.status != "em_processamento":
        raise HTTPException(
            status_code=400,
            detail="Apenas operacoes em processamento podem ser finalizadas",
        )

    # Buscar boletos e XMLs
    boletos_result = await db.execute(
        select(Boleto).where(Boleto.operacao_id == op.id).order_by(Boleto.created_at)
    )
    todos_boletos = boletos_result.scalars().all()

    xmls_result = await db.execute(
        select(XmlNfe).where(XmlNfe.operacao_id == op.id)
    )
    xmls = xmls_result.scalars().all()
    xmls_map = {str(x.id): x for x in xmls}

    # Separar aprovados e rejeitados
    aprovados = [b for b in todos_boletos if b.status == "aprovado"]
    rejeitados = [b for b in todos_boletos if b.status == "rejeitado"]

    relatorio_gerado = False
    try:
        # Gerar relatorios
        if aprovados:
            gerar_relatorio_aprovados_txt(op, aprovados, xmls_map)
        if rejeitados:
            gerar_relatorio_erros_txt(op, rejeitados)
        gerar_relatorio_json(op, todos_boletos, xmls_map)
        relatorio_gerado = True
    except Exception:
        pass  # Relatorio falhou mas finalizacao continua

    # Mudar status
    op.status = "concluida"

    await registrar_audit(
        db, acao="finalizar_operacao", operacao_id=op.id,
        usuario_id=current_user.id, entidade="operacao",
        detalhes={
            "total_boletos": op.total_boletos,
            "aprovados": op.total_aprovados,
            "rejeitados": op.total_rejeitados,
            "taxa_sucesso": op.taxa_sucesso,
            "relatorio_gerado": relatorio_gerado,
        },
    )
    await db.commit()

    return OperacaoFinalizada(
        id=op.id,
        status=op.status,
        total_boletos=op.total_boletos,
        total_aprovados=op.total_aprovados,
        total_rejeitados=op.total_rejeitados,
        taxa_sucesso=op.taxa_sucesso,
        valor_bruto=op.valor_bruto,
        valor_liquido=op.valor_liquido,
        relatorio_gerado=relatorio_gerado,
    )


# ── POST /operacoes/{id}/cancelar ────────────────────────────


@router.post("/{op_id}/cancelar", response_model=OperacaoResponse)
async def cancelar_operacao(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Cancela operacao (muda status para cancelada)."""
    op = await _get_operacao(op_id, db)

    if op.status != "em_processamento":
        raise HTTPException(
            status_code=400,
            detail="Apenas operacoes em processamento podem ser canceladas",
        )

    op.status = "cancelada"

    await registrar_audit(
        db, acao="cancelar_operacao", operacao_id=op.id,
        usuario_id=current_user.id, entidade="operacao",
        detalhes={"numero": op.numero},
    )
    await db.commit()
    await db.refresh(op)

    fidc = await _get_fidc(op.fidc_id, db)
    resp = OperacaoResponse.model_validate(op)
    resp.fidc_nome = fidc.nome
    return resp


# ── DELETE /operacoes/{id} ────────────────────────────────────


@router.delete("/{op_id}", status_code=status.HTTP_200_OK)
async def excluir_operacao(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Exclui operacao e todos os dados relacionados (boletos, XMLs, envios, audit logs)."""
    op = await _get_operacao(op_id, db)

    numero = op.numero

    # Deletar registros filhos (sem CASCADE no banco)
    await db.execute(delete(AuditLog).where(AuditLog.operacao_id == op.id))
    await db.execute(delete(Envio).where(Envio.operacao_id == op.id))
    await db.execute(delete(Boleto).where(Boleto.operacao_id == op.id))
    await db.execute(delete(XmlNfe).where(XmlNfe.operacao_id == op.id))
    await db.delete(op)

    # Remover pasta de arquivos
    upload_dir = _storage_path() / "uploads" / str(op.id)
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)

    await db.commit()

    return {"detail": f"Operacao {numero} excluida com sucesso"}


# ── POST /operacoes/{id}/enviar ──────────────────────────────


@router.post("/{op_id}/enviar", response_model=EnvioResultado)
async def enviar_operacao(
    op_id: str,
    body: EnvioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Envia boletos aprovados via SMTP (preview = rascunho no banco, automatico = envio direto)."""
    op = await _get_operacao(op_id, db)

    if op.status not in ("em_processamento", "concluida"):
        raise HTTPException(
            status_code=400,
            detail="Operacao deve estar em processamento ou concluida para enviar",
        )

    if body.modo not in ("preview", "automatico"):
        raise HTTPException(
            status_code=400,
            detail="Modo invalido. Use: preview ou automatico",
        )

    fidc = await _get_fidc(op.fidc_id, db)

    # Buscar boletos aprovados
    boletos_result = await db.execute(
        select(Boleto)
        .where(Boleto.operacao_id == op.id)
        .where(Boleto.status == "aprovado")
    )
    boletos_aprovados = boletos_result.scalars().all()

    if not boletos_aprovados:
        raise HTTPException(
            status_code=400,
            detail="Nenhum boleto aprovado para enviar",
        )

    # Buscar XMLs
    xmls_result = await db.execute(
        select(XmlNfe).where(XmlNfe.operacao_id == op.id)
    )
    xmls = xmls_result.scalars().all()

    # Buscar layout de email ativo
    layout_result = await db.execute(select(EmailLayout).where(EmailLayout.ativo == True))
    active_layout = layout_result.scalar_one_or_none()
    layout_dict = None
    if active_layout:
        layout_dict = {
            "saudacao": active_layout.saudacao,
            "introducao": active_layout.introducao,
            "mensagem_fechamento": active_layout.mensagem_fechamento,
            "assinatura_nome": active_layout.assinatura_nome,
        }

    # Override com textos do FIDC (se definidos)
    if layout_dict is None:
        layout_dict = {}
    if fidc.email_introducao:
        layout_dict["introducao"] = fidc.email_introducao
    if fidc.email_mensagem_fechamento:
        layout_dict["mensagem_fechamento"] = fidc.email_mensagem_fechamento
    if fidc.email_assinatura_nome:
        layout_dict["assinatura_nome"] = fidc.email_assinatura_nome

    # Agrupar por email destino
    storage_base = _storage_path() / "uploads" / str(op.id)
    grupos = agrupar_boletos_para_envio(boletos_aprovados, xmls, fidc, storage_base, email_layout=layout_dict)

    if not grupos:
        raise HTTPException(
            status_code=400,
            detail="Nenhum email destino encontrado nos XMLs vinculados",
        )

    # Instanciar mailer SMTP
    mailer = SMTPMailer(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        from_email=settings.SMTP_FROM_EMAIL,
        from_name=settings.SMTP_FROM_NAME,
    )

    detalhes: list[EnvioDetalhe] = []
    emails_enviados = 0

    for group in grupos:
        # Criar registro Envio no banco
        envio = Envio(
            operacao_id=op.id,
            usuario_id=current_user.id,
            email_para=group.email_para,
            email_cc=group.email_cc,
            assunto=group.assunto,
            corpo_html=group.corpo_html,
            modo=body.modo,
            status="pendente",
            boletos_ids=[uuid.UUID(bid) for bid in group.boletos_ids],
            xmls_anexados=group.xmls_nomes,
        )
        db.add(envio)
        await db.flush()

        # Enviar ou criar rascunho
        try:
            if body.modo == "preview":
                mailer.create_draft(group)
                envio.status = "rascunho"
            else:
                mailer.send_email(group)
                envio.status = "enviado"
                envio.timestamp_envio = datetime.now(timezone.utc)
                emails_enviados += 1
        except RuntimeError as e:
            envio.status = "erro"
            envio.erro_detalhes = str(e)

        detalhes.append(EnvioDetalhe(
            email_para=group.email_para,
            email_cc=group.email_cc,
            assunto=group.assunto,
            boletos_count=len(group.boletos_ids),
            xmls_count=len(group.xmls_nomes),
            status=envio.status,
        ))

    # Atualizar modo_envio na operacao
    op.modo_envio = body.modo

    await registrar_audit(
        db, acao="enviar_operacao", operacao_id=op.id,
        usuario_id=current_user.id, entidade="envio",
        detalhes={
            "modo": body.modo,
            "emails_criados": len(grupos),
            "emails_enviados": emails_enviados,
        },
    )
    await db.commit()

    return EnvioResultado(
        emails_criados=len(grupos),
        emails_enviados=emails_enviados,
        modo=body.modo,
        detalhes=detalhes,
    )


# ── GET /operacoes/{id}/envios ──────────────────────────────


@router.get("/{op_id}/envios", response_model=list[EnvioResponse])
async def listar_envios(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Lista todos os envios de uma operacao."""
    await _get_operacao(op_id, db)  # Valida que existe

    result = await db.execute(
        select(Envio)
        .where(Envio.operacao_id == op_id)
        .order_by(Envio.created_at.desc())
    )
    envios = result.scalars().all()

    return [EnvioResponse.model_validate(e) for e in envios]


# ── POST /operacoes/{id}/envios/{envio_id}/confirmar ──────────


@router.post("/{op_id}/envios/{envio_id}/confirmar", response_model=EnvioResponse)
async def confirmar_envio(
    op_id: str,
    envio_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Confirma e envia um rascunho via SMTP."""
    op = await _get_operacao(op_id, db)

    result = await db.execute(
        select(Envio).where(Envio.id == envio_id, Envio.operacao_id == op_id)
    )
    envio = result.scalar_one_or_none()
    if not envio:
        raise HTTPException(status_code=404, detail="Envio nao encontrado")

    if envio.status != "rascunho":
        raise HTTPException(
            status_code=400,
            detail="Apenas envios com status 'rascunho' podem ser confirmados",
        )

    group = await _reconstruir_email_group(envio, op, db)

    mailer = SMTPMailer(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        from_email=settings.SMTP_FROM_EMAIL,
        from_name=settings.SMTP_FROM_NAME,
    )

    try:
        mailer.send_email(group)
        envio.status = "enviado"
        envio.timestamp_envio = datetime.now(timezone.utc)
    except RuntimeError as e:
        envio.status = "erro"
        envio.erro_detalhes = str(e)

    await registrar_audit(
        db,
        acao="confirmar_envio_smtp",
        operacao_id=op.id,
        usuario_id=current_user.id,
        entidade="envio",
        entidade_id=str(envio.id),
        detalhes={"status": envio.status},
    )
    await db.commit()
    await db.refresh(envio)

    return EnvioResponse.model_validate(envio)


# ── POST /operacoes/{id}/envios/confirmar-todos ──────────────


@router.post("/{op_id}/envios/confirmar-todos", response_model=EnvioResultado)
async def confirmar_todos_envios(
    op_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Confirma e envia todos os rascunhos SMTP de uma operacao."""
    op = await _get_operacao(op_id, db)

    result = await db.execute(
        select(Envio)
        .where(Envio.operacao_id == op_id, Envio.status == "rascunho")
    )
    rascunhos = result.scalars().all()

    if not rascunhos:
        raise HTTPException(status_code=400, detail="Nenhum rascunho pendente")

    mailer = SMTPMailer(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        from_email=settings.SMTP_FROM_EMAIL,
        from_name=settings.SMTP_FROM_NAME,
    )

    detalhes: list[EnvioDetalhe] = []
    emails_enviados = 0

    for envio in rascunhos:
        group = await _reconstruir_email_group(envio, op, db)

        try:
            mailer.send_email(group)
            envio.status = "enviado"
            envio.timestamp_envio = datetime.now(timezone.utc)
            emails_enviados += 1
        except RuntimeError as e:
            envio.status = "erro"
            envio.erro_detalhes = str(e)

        detalhes.append(EnvioDetalhe(
            email_para=envio.email_para,
            email_cc=envio.email_cc,
            assunto=envio.assunto,
            boletos_count=len(envio.boletos_ids),
            xmls_count=len(envio.xmls_anexados),
            status=envio.status,
        ))

    await registrar_audit(
        db,
        acao="confirmar_todos_envios_smtp",
        operacao_id=op.id,
        usuario_id=current_user.id,
        entidade="envio",
        detalhes={
            "total_rascunhos": len(rascunhos),
            "emails_enviados": emails_enviados,
        },
    )
    await db.commit()

    return EnvioResultado(
        emails_criados=len(rascunhos),
        emails_enviados=emails_enviados,
        modo="confirmar",
        detalhes=detalhes,
    )


# ── PATCH /operacoes/{id}/xmls/{xml_id}/emails ───────────────


@router.patch("/{op_id}/xmls/{xml_id}/emails", response_model=XmlResumo)
async def atualizar_emails_xml(
    op_id: str,
    xml_id: str,
    body: XmlEmailsUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Edita os emails de destino de um XML."""
    import re

    await _get_operacao(op_id, db)

    result = await db.execute(
        select(XmlNfe).where(XmlNfe.id == xml_id, XmlNfe.operacao_id == op_id)
    )
    xml = result.scalar_one_or_none()
    if not xml:
        raise HTTPException(status_code=404, detail="XML nao encontrado")

    email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    valid_emails: list[str] = []
    invalid_emails: list[str] = []
    for email in body.emails:
        email = email.strip()
        if not email:
            continue
        if email_pattern.match(email):
            valid_emails.append(email)
        else:
            invalid_emails.append(email)

    xml.emails = valid_emails
    xml.emails_invalidos = invalid_emails

    await db.commit()
    await db.refresh(xml)

    return XmlResumo.model_validate(xml)


# ── PATCH /operacoes/{id}/envios/{envio_id}/status ──────────


@router.patch("/{op_id}/envios/{envio_id}/status", response_model=EnvioResponse)
async def atualizar_status_envio(
    op_id: str,
    envio_id: str,
    body: EnvioStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Marca manualmente um envio como enviado."""
    await _get_operacao(op_id, db)

    result = await db.execute(
        select(Envio).where(Envio.id == envio_id, Envio.operacao_id == op_id)
    )
    envio = result.scalar_one_or_none()
    if not envio:
        raise HTTPException(status_code=404, detail="Envio nao encontrado")

    if envio.status == body.status:
        return EnvioResponse.model_validate(envio)

    status_anterior = envio.status
    envio.status = body.status
    if body.status == "enviado":
        envio.timestamp_envio = datetime.now(timezone.utc)

    await registrar_audit(
        db,
        acao="envio_status_manual",
        operacao_id=uuid.UUID(op_id),
        usuario_id=current_user.id,
        entidade="envio",
        entidade_id=str(envio.id),
        detalhes={"de": status_anterior, "para": body.status, "via": "manual"},
    )

    await db.commit()
    await db.refresh(envio)

    return EnvioResponse.model_validate(envio)


# ── GET /operacoes/{id}/relatorio ────────────────────────────


@router.get("/{op_id}/relatorio")
async def download_relatorio(
    op_id: str,
    formato: str = "json",
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Download de relatorio da operacao finalizada.

    Parametros:
        formato: 'json' | 'txt_aprovados' | 'txt_erros'
    """
    op = await _get_operacao(op_id, db)

    if op.status != "concluida":
        raise HTTPException(
            status_code=400,
            detail="Relatorios so estao disponiveis para operacoes concluidas",
        )

    storage = Path(settings.STORAGE_DIR)

    if formato == "json":
        search_dir = storage / "auditoria"
        prefix = "auditoria_"
        media_type = "application/json"
    elif formato == "txt_aprovados":
        search_dir = storage / "auditoria"
        prefix = "auditoria_aprovados_"
        media_type = "text/plain"
    elif formato == "txt_erros":
        search_dir = storage / "erros"
        prefix = "erros_"
        media_type = "text/plain"
    else:
        raise HTTPException(
            status_code=400,
            detail="Formato invalido. Use: json, txt_aprovados, txt_erros",
        )

    if not search_dir.exists():
        raise HTTPException(status_code=404, detail="Relatorio nao encontrado")

    # Buscar o relatorio mais recente com o prefixo
    files = sorted(search_dir.glob(f"{prefix}*"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="Relatorio nao encontrado")

    return FileResponse(
        path=str(files[0]),
        media_type=media_type,
        filename=files[0].name,
    )


# ── Funcoes auxiliares internas ──────────────────────────────


def _extrair_texto_pdf(file_path: str | None) -> str:
    """Extrai texto completo de um PDF via pdfplumber."""  # noqa: D401
    if not file_path:
        return ""
    try:
        with pdfplumber.open(file_path) as pdf:
            texts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n".join(texts)
    except Exception:
        return ""


def _parse_vencimento_date(vencimento_completo: str | None):
    """Converte DD/MM/YYYY para date ou None."""
    if not vencimento_completo:
        return None
    try:
        from datetime import datetime as dt

        return dt.strptime(vencimento_completo, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _camada_to_dict(camada) -> dict | None:
    """Converte ResultadoCamada para dict serializável."""
    if camada is None:
        return None
    return {
        "camada": camada.camada,
        "nome": camada.nome,
        "aprovado": camada.aprovado,
        "mensagem": camada.mensagem,
        "bloqueia": camada.bloqueia,
        "detalhes": camada.detalhes,
    }


def _renomear_arquivo(original: Path, novo_nome: str) -> None:
    """Renomeia arquivo no filesystem."""
    if not original.exists():
        return
    novo_path = original.parent / novo_nome
    if novo_path != original:
        shutil.move(str(original), str(novo_path))


async def _reconstruir_email_group(envio: Envio, op: Operacao, db: AsyncSession) -> EmailGroup:
    """Reconstroi EmailGroup a partir de um registro Envio para reenvio via SMTP."""
    storage_base = _storage_path() / "uploads" / str(op.id)

    # Buscar boletos para paths dos anexos PDF
    anexos_pdf: list[Path] = []
    if envio.boletos_ids:
        boletos_result = await db.execute(
            select(Boleto).where(Boleto.id.in_(envio.boletos_ids))
        )
        for b in boletos_result.scalars().all():
            if b.arquivo_path:
                pdf_path = Path(b.arquivo_path)
                if b.arquivo_renomeado:
                    renamed = pdf_path.parent / b.arquivo_renomeado
                    if renamed.exists():
                        pdf_path = renamed
                if pdf_path.exists():
                    anexos_pdf.append(pdf_path)

    # Buscar NF PDFs — encontrar PDF correspondente pelo numero_nota
    anexos_xml: list[Path] = []
    if envio.xmls_anexados:
        xmls_result = await db.execute(
            select(XmlNfe).where(
                XmlNfe.operacao_id == op.id,
                XmlNfe.nome_arquivo.in_(envio.xmls_anexados),
            )
        )
        xml_records = xmls_result.scalars().all()

        # Buscar todos os PDFs de NF da operacao
        all_xmls_result = await db.execute(
            select(XmlNfe).where(XmlNfe.operacao_id == op.id)
        )
        all_xmls = all_xmls_result.scalars().all()
        nf_pdfs_by_nota: dict[str, XmlNfe] = {}
        for x in all_xmls:
            if x.nome_arquivo.lower().endswith(".pdf"):
                nf_key = (x.numero_nota or "").lstrip("0") or "0"
                nf_pdfs_by_nota[nf_key] = x

        nf_dir = storage_base / "xmls"
        for xml_rec in xml_records:
            nf_key = (xml_rec.numero_nota or "").lstrip("0") or "0"
            nf_pdf = nf_pdfs_by_nota.get(nf_key)
            if nf_pdf:
                nf_pdf_path = nf_dir / nf_pdf.nome_arquivo
                if nf_pdf_path.exists():
                    anexos_xml.append(nf_pdf_path)

    return EmailGroup(
        email_para=envio.email_para,
        email_cc=envio.email_cc,
        assunto=envio.assunto,
        corpo_html=envio.corpo_html or "",
        boletos_ids=[str(bid) for bid in envio.boletos_ids],
        xmls_ids=[],
        xmls_nomes=envio.xmls_anexados,
        anexos_pdf=anexos_pdf,
        anexos_xml=anexos_xml,
    )
