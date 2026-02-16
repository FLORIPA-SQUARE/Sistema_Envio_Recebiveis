from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.fidc import Fidc
from app.models.usuario import Usuario
from app.schemas.fidc import FidcCreate, FidcResponse, FidcUpdate
from app.security import get_current_user

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
