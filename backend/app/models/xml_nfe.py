import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class XmlNfe(Base):
    __tablename__ = "xmls_nfe"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operacoes.id"), nullable=False)
    nome_arquivo: Mapped[str] = mapped_column(String(500), nullable=False)
    numero_nota: Mapped[str] = mapped_column(String(20), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(20), nullable=True)
    nome_destinatario: Mapped[str] = mapped_column(String(300), nullable=True)
    valor_total: Mapped[float] = mapped_column(Float, nullable=True)
    emails: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    emails_invalidos: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    duplicatas: Mapped[dict] = mapped_column(JSONB, default=list)
    xml_valido: Mapped[bool] = mapped_column(Boolean, default=True)
    dados_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
