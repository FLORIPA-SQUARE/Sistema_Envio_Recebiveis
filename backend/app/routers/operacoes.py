"""
Router de Operacoes — CRUD, upload, processamento, reprocessamento, finalizacao, envio.

Endpoints:
  POST   /operacoes                      — Criar operacao
  GET    /operacoes                      — Listar (paginado)
  GET    /operacoes/dashboard/stats      — KPIs agregados
  GET    /operacoes/{id}                 — Detalhes com boletos + XMLs
  DELETE /operacoes/{id}                 — Excluir operacao e dados relacionados
  POST   /operacoes/{id}/boletos/upload  — Upload PDFs (multipart + auto-split)
  POST   /operacoes/{id}/xmls/upload     — Upload XMLs (batch)
  POST   /operacoes/{id}/processar       — Extracao + renomeacao + validacao 5 camadas
  POST   /operacoes/{id}/reprocessar     — Reprocessar boletos rejeitados
  POST   /operacoes/{id}/finalizar       — Finalizar operacao + gerar relatorios
  POST   /operacoes/{id}/cancelar        — Cancelar operacao
  POST   /operacoes/{id}/enviar          — Enviar emails via Outlook (preview/automatico)
  GET    /operacoes/{id}/envios          — Listar envios da operacao
  GET    /operacoes/{id}/relatorio       — Download de relatorio (TXT/JSON)
"""

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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
    BoletoResumo,
    DashboardStats,
    EnvioDetalhe,
    EnvioRequest,
    EnvioResponse,
    EnvioResultado,
    OperacaoCreate,
    OperacaoDetalhada,
    OperacaoFinalizada,
    OperacaoResponse,
    OperacoesPaginadas,
    ResultadoProcessamento,
    UploadBoletosResponse,
    UploadXmlsResponse,
    XmlResumo,
)
from app.schemas.fidc import FidcResponse
from app.security import get_current_user
from app.services.audit import registrar_audit
from app.services.pdf_splitter import split_pdf
from app.services.email_grouper import agrupar_boletos_para_envio
from app.services.outlook_mailer import OutlookMailer
from app.services.report_generator import (
    gerar_relatorio_aprovados_txt,
    gerar_relatorio_erros_txt,
    gerar_relatorio_json,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operacoes", tags=["operacoes"])


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

    # Gera número automático se não fornecido
    numero = body.numero
    if not numero:
        count_result = await db.execute(select(func.count()).select_from(Operacao))
        count = count_result.scalar() or 0
        numero = f"OP-{count + 1:04d}"

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

    items = []
    for o in ops:
        resp = OperacaoResponse.model_validate(o)
        resp.fidc_nome = fidcs_map.get(o.fidc_id)
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

    recentes_resp = []
    for o in recentes:
        resp = OperacaoResponse.model_validate(o)
        resp.fidc_nome = fidcs_map.get(o.fidc_id)
        recentes_resp.append(resp)

    return DashboardStats(
        total_operacoes=total_ops,
        total_boletos=total_boletos,
        total_aprovados=total_aprovados,
        total_rejeitados=total_rejeitados,
        taxa_sucesso_global=round(taxa, 2),
        operacoes_recentes=recentes_resp,
    )


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

    # Verificar duplicatas — buscar nomes de arquivos ja enviados
    existing = await db.execute(
        select(Boleto.arquivo_original).where(Boleto.operacao_id == op.id)
    )
    existing_names = {row[0] for row in existing.all()}

    op_dir = _operacao_dir(op.id)
    boletos_dir = op_dir / "boletos"
    split_dir = op_dir / "boletos_split"
    boletos_dir.mkdir(parents=True, exist_ok=True)
    split_dir.mkdir(parents=True, exist_ok=True)

    total_paginas = 0
    boletos_criados: list[BoletoResumo] = []

    for file in files:
        # Validação: apenas PDF
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Formato invalido: {file.filename}. Apenas arquivos PDF sao aceitos.",
            )

        # Verificar duplicata
        if file.filename in existing_names:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo duplicado: {file.filename} ja foi enviado nesta operacao.",
            )

        # Salva arquivo original
        orig_path = boletos_dir / file.filename
        content = await file.read()
        orig_path.write_bytes(content)

        # Auto-split
        split_files = split_pdf(orig_path, split_dir)
        total_paginas += len(split_files)

        # Cria registro no banco para cada página
        for sf in split_files:
            boleto = Boleto(
                operacao_id=op.id,
                arquivo_original=sf.name,
                arquivo_path=str(sf),
            )
            db.add(boleto)
            await db.flush()
            boletos_criados.append(BoletoResumo(id=boleto.id, arquivo_original=sf.name))

    # Atualiza total na operação
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

    # Verificar duplicatas — buscar nomes de arquivos ja enviados
    existing_nf = await db.execute(
        select(XmlNfe.nome_arquivo).where(XmlNfe.operacao_id == op.id)
    )
    existing_nf_names = {row[0] for row in existing_nf.all()}

    op_dir = _operacao_dir(op.id)
    xmls_dir = op_dir / "xmls"
    xmls_dir.mkdir(parents=True, exist_ok=True)

    xmls_result: list[XmlResumo] = []
    validos = 0
    invalidos = 0

    for file in files:
        # Validação: XML ou PDF
        if not file.filename or not file.filename.lower().endswith((".xml", ".pdf")):
            raise HTTPException(
                status_code=400,
                detail=f"Formato invalido: {file.filename}. Apenas arquivos XML ou PDF sao aceitos.",
            )

        # Verificar duplicata
        if file.filename in existing_nf_names:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo duplicado: {file.filename} ja foi enviado nesta operacao.",
            )

        # Salva arquivo
        nf_path = xmls_dir / file.filename
        content = await file.read()
        nf_path.write_bytes(content)

        is_pdf = file.filename.lower().endswith(".pdf")

        if is_pdf:
            # PDF de nota fiscal — salvar como anexo sem parse
            # Extrair numero da nota do nome do arquivo (ex: 3-0318865.pdf → 0318865)
            stem = nf_path.stem
            numero_nota = stem.split("-")[-1] if "-" in stem else stem

            xml_record = XmlNfe(
                operacao_id=op.id,
                nome_arquivo=file.filename,
                numero_nota=numero_nota,
                cnpj=None,
                nome_destinatario=None,
                valor_total=None,
                emails=[],
                emails_invalidos=[],
                duplicatas=[],
                xml_valido=True,
                dados_raw={},
            )
            db.add(xml_record)
            await db.flush()
            validos += 1
        else:
            # Parse XML NFe
            dados = parse_xml_nfe(nf_path)

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

        # Renomear arquivo fisicamente
        if boleto.arquivo_path and resultado.aprovado:
            _renomear_arquivo(Path(boleto.arquivo_path), nome_renomeado)

        boletos_processados.append(BoletoCompleto.model_validate(boleto))

    # Atualizar totais da operacao
    total = aprovados + rejeitados
    op.total_boletos = total
    op.total_aprovados = aprovados
    op.total_rejeitados = rejeitados
    op.taxa_sucesso = (aprovados / total * 100) if total > 0 else 0.0

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
    """Envia boletos aprovados via Outlook (preview = rascunho, automatico = envio direto)."""
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

    # Agrupar por email destino
    storage_base = _storage_path() / "uploads" / str(op.id)
    grupos = agrupar_boletos_para_envio(boletos_aprovados, xmls, fidc, storage_base)

    if not grupos:
        raise HTTPException(
            status_code=400,
            detail="Nenhum email destino encontrado nos XMLs vinculados",
        )

    # Instanciar mailer
    mailer = OutlookMailer()

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
