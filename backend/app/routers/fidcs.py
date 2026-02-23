from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.email_layout import EmailLayout
from app.models.fidc import Fidc
from app.models.usuario import Usuario
from app.schemas.fidc import (
    FidcCreate,
    FidcEmailPreviewRequest,
    FidcEmailPreviewResponse,
    FidcResponse,
    FidcUpdate,
)
from app.security import get_current_user
from app.services.email_template import gerar_email_html

router = APIRouter(prefix="/fidcs", tags=["fidcs"])


@router.get("", response_model=list[FidcResponse])
async def list_fidcs(
    ativo: bool | None = Query(None, description="Filtrar por status ativo/inativo"),
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    query = select(Fidc).order_by(Fidc.nome)
    if ativo is not None:
        query = query.where(Fidc.ativo == ativo)
    result = await db.execute(query)
    fidcs = result.scalars().all()
    return [FidcResponse.model_validate(f) for f in fidcs]


@router.post("", response_model=FidcResponse, status_code=status.HTTP_201_CREATED)
async def create_fidc(
    body: FidcCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    existing = await db.execute(select(Fidc).where(Fidc.nome == body.nome))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ja existe um FIDC com o nome '{body.nome}'",
        )

    fidc = Fidc(**body.model_dump())
    db.add(fidc)
    await db.commit()
    await db.refresh(fidc)
    return FidcResponse.model_validate(fidc)


_SAMPLE_BOLETOS = [
    {
        "numero_nota": "12345",
        "valor_formatado": "R$ 1.500,00",
        "vencimento_completo": "15/03/2026",
    },
    {
        "numero_nota": "12346",
        "valor_formatado": "R$ 2.300,00",
        "vencimento_completo": "20/03/2026",
    },
]


@router.post("/preview-email", response_model=FidcEmailPreviewResponse)
async def preview_email_fidc(
    body: FidcEmailPreviewRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    """Gera preview HTML do email com dados de exemplo e textos do FIDC."""
    # Buscar layout ativo para fallback (mesma logica do envio real)
    layout_result = await db.execute(
        select(EmailLayout).where(EmailLayout.ativo == True)
    )
    active_layout = layout_result.scalar_one_or_none()

    # Construir kwargs: layout ativo → FIDC override → defaults de gerar_email_html
    kwargs: dict = {}
    if active_layout:
        if active_layout.introducao:
            kwargs["introducao"] = active_layout.introducao
        if active_layout.mensagem_fechamento:
            kwargs["mensagem_fechamento"] = active_layout.mensagem_fechamento
        if active_layout.assinatura_nome:
            kwargs["assinatura_nome"] = active_layout.assinatura_nome

    if body.email_introducao and body.email_introducao.strip():
        kwargs["introducao"] = body.email_introducao.strip()
    if body.email_mensagem_fechamento and body.email_mensagem_fechamento.strip():
        kwargs["mensagem_fechamento"] = body.email_mensagem_fechamento.strip()
    if body.email_assinatura_nome and body.email_assinatura_nome.strip():
        kwargs["assinatura_nome"] = body.email_assinatura_nome.strip()

    html = gerar_email_html(
        nome_cliente="EMPRESA EXEMPLO LTDA",
        boletos_info=_SAMPLE_BOLETOS,
        nome_fidc_completo=body.nome_completo or "FIDC EXEMPLO",
        cnpj_fidc=body.cnpj or "00.000.000/0001-00",
        **kwargs,
    )

    return FidcEmailPreviewResponse(html=html)


@router.put("/{fidc_id}", response_model=FidcResponse)
async def update_fidc(
    fidc_id: str,
    body: FidcUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Fidc).where(Fidc.id == fidc_id))
    fidc = result.scalar_one_or_none()
    if not fidc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FIDC não encontrado")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fidc, field, value)

    await db.commit()
    await db.refresh(fidc)
    return FidcResponse.model_validate(fidc)
