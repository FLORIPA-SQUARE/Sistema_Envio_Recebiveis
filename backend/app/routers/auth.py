from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioResponse
from app.security import create_access_token, get_current_user, verify_password
from app.services.audit import registrar_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado",
        )

    token = create_access_token({"sub": str(user.id)})

    await registrar_audit(
        db, acao="login", usuario_id=user.id,
        entidade="usuario", detalhes={"email": user.email},
    )
    await db.commit()

    return LoginResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(user),
    )


@router.get("/me", response_model=UsuarioResponse)
async def me(current_user: Usuario = Depends(get_current_user)):
    return UsuarioResponse.model_validate(current_user)
