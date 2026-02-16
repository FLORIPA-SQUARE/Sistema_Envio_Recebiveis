import uuid
from datetime import datetime

from pydantic import BaseModel


class FidcResponse(BaseModel):
    id: uuid.UUID
    nome: str
    nome_completo: str
    cnpj: str | None
    cc_emails: list[str]
    palavras_chave: list[str]
    cor: str
    ativo: bool
    email_introducao: str | None = None
    email_mensagem_fechamento: str | None = None
    email_assinatura_nome: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FidcCreate(BaseModel):
    nome: str
    nome_completo: str
    cnpj: str | None = None
    cc_emails: list[str] = []
    palavras_chave: list[str] = []
    cor: str = "#999999"
    email_introducao: str | None = None
    email_mensagem_fechamento: str | None = None
    email_assinatura_nome: str | None = None


class FidcUpdate(BaseModel):
    nome_completo: str | None = None
    cnpj: str | None = None
    cc_emails: list[str] | None = None
    palavras_chave: list[str] | None = None
    cor: str | None = None
    ativo: bool | None = None
    email_introducao: str | None = None
    email_mensagem_fechamento: str | None = None
    email_assinatura_nome: str | None = None
