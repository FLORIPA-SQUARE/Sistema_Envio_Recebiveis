import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Operacao(Base):
    __tablename__ = "operacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    fidc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fidcs.id"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="em_processamento"
    )  # em_processamento | enviando | concluida | cancelada
    modo_envio: Mapped[str] = mapped_column(String(20), nullable=False, default="preview")  # preview | automatico
    total_boletos: Mapped[int] = mapped_column(Integer, default=0)
    total_aprovados: Mapped[int] = mapped_column(Integer, default=0)
    total_rejeitados: Mapped[int] = mapped_column(Integer, default=0)
    taxa_sucesso: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
