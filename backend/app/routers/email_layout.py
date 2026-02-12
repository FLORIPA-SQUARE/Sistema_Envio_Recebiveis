from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.email_layout import EmailLayout
from app.models.usuario import Usuario
from app.schemas.email_layout import EmailLayoutCreate, EmailLayoutResponse, EmailLayoutUpdate
from app.security import get_current_user

router = APIRouter(prefix="/configuracao/email-layouts", tags=["email-layouts"])

MAX_LAYOUTS = 3


@router.get("", response_model=list[EmailLayoutResponse])
async def list_layouts(
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(EmailLayout).order_by(EmailLayout.created_at))
    layouts = result.scalars().all()
    return [EmailLayoutResponse.model_validate(l) for l in layouts]


@router.post("", response_model=EmailLayoutResponse, status_code=status.HTTP_201_CREATED)
async def create_layout(
    body: EmailLayoutCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    count_result = await db.execute(select(func.count()).select_from(EmailLayout))
    count = count_result.scalar() or 0
    if count >= MAX_LAYOUTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {MAX_LAYOUTS} layouts atingido",
        )

    existing = await db.execute(select(EmailLayout).where(EmailLayout.nome == body.nome))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ja existe um layout com o nome '{body.nome}'",
        )

    is_first = count == 0
    layout = EmailLayout(
        nome=body.nome,
        saudacao=body.saudacao,
        introducao=body.introducao,
        mensagem_fechamento=body.mensagem_fechamento,
        assinatura_nome=body.assinatura_nome,
        ativo=is_first,
    )
    db.add(layout)
    await db.commit()
    await db.refresh(layout)
    return EmailLayoutResponse.model_validate(layout)


@router.put("/{layout_id}", response_model=EmailLayoutResponse)
async def update_layout(
    layout_id: str,
    body: EmailLayoutUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(EmailLayout).where(EmailLayout.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout nao encontrado")

    update_data = body.model_dump(exclude_unset=True)

    if "nome" in update_data and update_data["nome"] != layout.nome:
        existing = await db.execute(
            select(EmailLayout).where(EmailLayout.nome == update_data["nome"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ja existe um layout com o nome '{update_data['nome']}'",
            )

    for field, value in update_data.items():
        setattr(layout, field, value)

    await db.commit()
    await db.refresh(layout)
    return EmailLayoutResponse.model_validate(layout)


@router.patch("/{layout_id}/ativar", response_model=EmailLayoutResponse)
async def ativar_layout(
    layout_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(EmailLayout).where(EmailLayout.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout nao encontrado")

    all_result = await db.execute(select(EmailLayout))
    for l in all_result.scalars().all():
        l.ativo = l.id == layout.id

    await db.commit()
    await db.refresh(layout)
    return EmailLayoutResponse.model_validate(layout)


@router.delete("/{layout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layout(
    layout_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(EmailLayout).where(EmailLayout.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout nao encontrado")

    if layout.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel excluir o layout ativo. Ative outro layout primeiro.",
        )

    await db.delete(layout)
    await db.commit()
