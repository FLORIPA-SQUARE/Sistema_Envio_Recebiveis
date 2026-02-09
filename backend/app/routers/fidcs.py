from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.fidc import Fidc
from app.models.usuario import Usuario
from app.schemas.fidc import FidcResponse, FidcUpdate
from app.security import get_current_user

router = APIRouter(prefix="/fidcs", tags=["fidcs"])


@router.get("", response_model=list[FidcResponse])
async def list_fidcs(
    db: AsyncSession = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Fidc).order_by(Fidc.nome))
    fidcs = result.scalars().all()
    return [FidcResponse.model_validate(f) for f in fidcs]


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
