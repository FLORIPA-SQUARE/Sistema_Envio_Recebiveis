import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Fidc(Base):
    __tablename__ = "fidcs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nome_completo: Mapped[str] = mapped_column(String(300), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(20), nullable=True)
    cc_emails: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    palavras_chave: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    cor: Mapped[str] = mapped_column(String(7), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    email_introducao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_mensagem_fechamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_assinatura_nome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
