import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Boleto(Base):
    __tablename__ = "boletos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operacoes.id"), nullable=False)
    xml_nfe_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("xmls_nfe.id"), nullable=True)
    arquivo_original: Mapped[str] = mapped_column(String(500), nullable=False)
    arquivo_renomeado: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pagador: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    numero_nota: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vencimento: Mapped[str | None] = mapped_column(String(10), nullable=True)  # DD-MM
    vencimento_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor: Mapped[float | None] = mapped_column(Float, nullable=True)
    valor_formatado: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fidc_detectada: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pendente")  # pendente | aprovado | parcialmente_aprovado | rejeitado
    motivo_rejeicao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    validacao_camada1: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validacao_camada2: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validacao_camada3: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validacao_camada4: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validacao_camada5: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    juros_detectado: Mapped[bool] = mapped_column(Boolean, default=False)
    arquivo_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
