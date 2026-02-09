import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Envio(Base):
    __tablename__ = "envios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operacoes.id"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    email_para: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    email_cc: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    assunto: Mapped[str] = mapped_column(String(500), nullable=False)
    corpo_html: Mapped[str] = mapped_column(Text, nullable=True)
    modo: Mapped[str] = mapped_column(String(20), nullable=False)  # preview | automatico
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pendente")  # pendente | enviado | erro
    erro_detalhes: Mapped[str | None] = mapped_column(Text, nullable=True)
    boletos_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    xmls_anexados: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    timestamp_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
