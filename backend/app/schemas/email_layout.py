import uuid
from datetime import datetime

from pydantic import BaseModel


class EmailLayoutCreate(BaseModel):
    nome: str
    saudacao: str = "auto"
    introducao: str
    mensagem_fechamento: str
    assinatura_nome: str


class EmailLayoutUpdate(BaseModel):
    nome: str | None = None
    saudacao: str | None = None
    introducao: str | None = None
    mensagem_fechamento: str | None = None
    assinatura_nome: str | None = None


class EmailLayoutResponse(BaseModel):
    id: uuid.UUID
    nome: str
    saudacao: str
    introducao: str
    mensagem_fechamento: str
    assinatura_nome: str
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
