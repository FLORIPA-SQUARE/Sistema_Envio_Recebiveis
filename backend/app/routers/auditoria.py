"""
Router de Auditoria — busca global de boletos por cliente, NF ou CNPJ.

Endpoints:
  GET /auditoria/buscar — Buscar boletos (paginado, com filtros)
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.boleto import Boleto
from app.models.fidc import Fidc
from app.models.operacao import Operacao
from app.models.usuario import Usuario
from app.models.xml_nfe import XmlNfe
from app.schemas.auditoria import AuditoriaBuscarResponse, AuditoriaItem
from app.security import get_current_user

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("/buscar", response_model=AuditoriaBuscarResponse)
async def buscar_auditoria(
    q: str = Query("", description="Termo de busca (NF, cliente, CNPJ)"),
    data_inicio: date | None = Query(None, description="Data inicio (YYYY-MM-DD)"),
    data_fim: date | None = Query(None, description="Data fim (YYYY-MM-DD)"),
    fidc_id: str | None = Query(None, description="Filtro por FIDC"),
    status: str | None = Query(None, description="Filtro por status do boleto"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Busca global de boletos por NF, nome do pagador ou CNPJ."""

    # Base: JOIN boletos -> operacoes -> fidcs
    query = (
        select(
            Boleto,
            Operacao.numero.label("op_numero"),
            Operacao.fidc_id.label("op_fidc_id"),
            Fidc.nome.label("fidc_nome"),
            Operacao.usuario_id.label("op_usuario_id"),
        )
        .join(Operacao, Boleto.operacao_id == Operacao.id)
        .join(Fidc, Operacao.fidc_id == Fidc.id)
        .where(Operacao.status == "concluida")
    )

    count_query = (
        select(func.count())
        .select_from(Boleto)
        .join(Operacao, Boleto.operacao_id == Operacao.id)
        .join(Fidc, Operacao.fidc_id == Fidc.id)
        .where(Operacao.status == "concluida")
    )

    # ── Text search (ILIKE com OR) ──
    if q and q.strip():
        term = f"%{q.strip()}%"
        text_filter = or_(
            Boleto.pagador.ilike(term),
            Boleto.numero_nota.ilike(term),
            Boleto.cnpj.ilike(term),
        )

        # Tambem buscar em xmls_nfe.nome_destinatario via subquery correlacionada
        xml_subq = (
            select(XmlNfe.id)
            .where(XmlNfe.nome_destinatario.ilike(term))
            .where(XmlNfe.id == Boleto.xml_nfe_id)
            .correlate(Boleto)
            .exists()
        )

        combined = or_(text_filter, xml_subq)
        query = query.where(combined)
        count_query = count_query.where(combined)

    # ── Date range ──
    if data_inicio:
        dt_inicio = datetime.combine(data_inicio, datetime.min.time())
        query = query.where(Boleto.created_at >= dt_inicio)
        count_query = count_query.where(Boleto.created_at >= dt_inicio)
    if data_fim:
        dt_fim = datetime.combine(data_fim, datetime.max.time())
        query = query.where(Boleto.created_at <= dt_fim)
        count_query = count_query.where(Boleto.created_at <= dt_fim)

    # ── FIDC filter ──
    if fidc_id:
        query = query.where(Operacao.fidc_id == fidc_id)
        count_query = count_query.where(Operacao.fidc_id == fidc_id)

    # ── Status filter ──
    if status:
        query = query.where(Boleto.status == status)
        count_query = count_query.where(Boleto.status == status)

    # ── Count total ──
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # ── Paginated results ──
    query = query.order_by(Boleto.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    # Resolver usuario_ids → nomes
    usuario_ids = list({row[4] for row in rows if row[4]})
    usuarios_map = {}
    if usuario_ids:
        usuarios_result = await db.execute(
            select(Usuario).where(Usuario.id.in_(usuario_ids))
        )
        usuarios_map = {u.id: u.nome for u in usuarios_result.scalars().all()}

    items = []
    for row in rows:
        boleto = row[0]
        op_numero = row[1]
        op_fidc_id = row[2]
        fidc_nome = row[3]
        op_usuario_id = row[4]

        items.append(AuditoriaItem(
            boleto_id=boleto.id,
            operacao_id=boleto.operacao_id,
            operacao_numero=op_numero,
            fidc_id=op_fidc_id,
            fidc_nome=fidc_nome,
            pagador=boleto.pagador,
            cnpj=boleto.cnpj,
            numero_nota=boleto.numero_nota,
            vencimento=boleto.vencimento,
            valor=boleto.valor,
            valor_formatado=boleto.valor_formatado,
            status=boleto.status,
            motivo_rejeicao=boleto.motivo_rejeicao,
            juros_detectado=boleto.juros_detectado,
            usuario_nome=usuarios_map.get(op_usuario_id),
            validacao_camada1=boleto.validacao_camada1,
            validacao_camada2=boleto.validacao_camada2,
            validacao_camada3=boleto.validacao_camada3,
            validacao_camada4=boleto.validacao_camada4,
            validacao_camada5=boleto.validacao_camada5,
            created_at=boleto.created_at,
        ))

    return AuditoriaBuscarResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
