import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditoriaItem(BaseModel):
    """Resultado individual de busca: um boleto com contexto da operacao/FIDC."""

    boleto_id: uuid.UUID
    operacao_id: uuid.UUID
    operacao_numero: str
    fidc_id: uuid.UUID
    fidc_nome: str
    pagador: str | None
    cnpj: str | None
    numero_nota: str | None
    vencimento: str | None
    valor: float | None
    valor_formatado: str | None
    status: str
    motivo_rejeicao: str | None
    juros_detectado: bool
    usuario_nome: str | None = None
    validacao_camada1: dict | None = None
    validacao_camada2: dict | None = None
    validacao_camada3: dict | None = None
    validacao_camada4: dict | None = None
    validacao_camada5: dict | None = None
    created_at: datetime


class AuditoriaBuscarResponse(BaseModel):
    """Resultado paginado da busca de auditoria."""

    items: list[AuditoriaItem]
    total: int
    page: int
    per_page: int
