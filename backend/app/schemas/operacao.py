import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.fidc import FidcResponse


# ── Request schemas ───────────────────────────────────────────


class XmlEmailsUpdate(BaseModel):
    emails: list[str]


class OperacaoCreate(BaseModel):
    fidc_id: uuid.UUID
    numero: str | None = None


class OperacaoUpdate(BaseModel):
    fidc_id: uuid.UUID | None = None
    numero: str | None = None


class ValorLiquidoUpdate(BaseModel):
    valor_liquido: float | None = None


# ── Response schemas ──────────────────────────────────────────


class OperacaoResponse(BaseModel):
    id: uuid.UUID
    numero: str
    fidc_id: uuid.UUID
    fidc_nome: str | None = None
    usuario_nome: str | None = None
    status: str
    modo_envio: str
    total_boletos: int
    total_aprovados: int
    total_rejeitados: int
    taxa_sucesso: float
    valor_bruto: float | None = None
    valor_liquido: float | None = None
    versao_finalizacao: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BoletoResumo(BaseModel):
    id: uuid.UUID
    arquivo_original: str

    model_config = {"from_attributes": True}


class BoletoCompleto(BaseModel):
    id: uuid.UUID
    arquivo_original: str
    arquivo_renomeado: str | None
    pagador: str | None
    cnpj: str | None
    numero_nota: str | None
    vencimento: str | None
    valor: float | None
    valor_formatado: str | None
    fidc_detectada: str | None
    status: str
    motivo_rejeicao: str | None
    validacao_camada1: dict | None = None
    validacao_camada2: dict | None = None
    validacao_camada3: dict | None = None
    validacao_camada4: dict | None = None
    validacao_camada5: dict | None = None
    juros_detectado: bool = False

    model_config = {"from_attributes": True}


class XmlResumo(BaseModel):
    id: uuid.UUID
    nome_arquivo: str
    numero_nota: str
    cnpj: str | None
    nome_destinatario: str | None
    valor_total: float | None
    emails: list[str]
    emails_invalidos: list[str]
    xml_valido: bool
    duplicatas: list[dict] = []

    model_config = {"from_attributes": True}


class OperacaoDetalhada(BaseModel):
    id: uuid.UUID
    numero: str
    fidc: FidcResponse
    status: str
    modo_envio: str
    total_boletos: int
    total_aprovados: int
    total_rejeitados: int
    taxa_sucesso: float
    valor_bruto: float | None = None
    valor_liquido: float | None = None
    versao_finalizacao: str | None = None
    created_at: datetime
    boletos: list[BoletoCompleto]
    xmls: list[XmlResumo]


class UploadBoletosResponse(BaseModel):
    total_paginas: int
    boletos_criados: int
    boletos: list[BoletoCompleto]


class UploadXmlsResponse(BaseModel):
    total_xmls: int
    validos: int
    invalidos: int
    xmls: list[XmlResumo]


class ResultadoProcessamento(BaseModel):
    total: int
    aprovados: int
    rejeitados: int
    taxa_sucesso: float
    valor_bruto: float | None = None
    boletos: list[BoletoCompleto]


class OperacoesPaginadas(BaseModel):
    items: list[OperacaoResponse]
    total: int
    page: int
    per_page: int


class DashboardStats(BaseModel):
    total_operacoes: int
    total_boletos: int
    total_aprovados: int
    total_rejeitados: int
    taxa_sucesso_global: float
    operacoes_recentes: list[OperacaoResponse]


class OperacaoFinalizada(BaseModel):
    id: uuid.UUID
    status: str
    total_boletos: int
    total_aprovados: int
    total_rejeitados: int
    taxa_sucesso: float
    valor_bruto: float | None = None
    valor_liquido: float | None = None
    versao_finalizacao: str | None = None
    relatorio_gerado: bool


# ── Envio schemas ────────────────────────────────────────────


class EnvioRequest(BaseModel):
    modo: str = "preview"  # "preview" | "automatico"


class EnvioDetalhe(BaseModel):
    email_para: list[str]
    email_cc: list[str]
    assunto: str
    boletos_count: int
    xmls_count: int
    status: str


class EnvioResultado(BaseModel):
    emails_criados: int
    emails_enviados: int
    modo: str
    detalhes: list[EnvioDetalhe]


class EnvioResponse(BaseModel):
    id: uuid.UUID
    email_para: list[str]
    email_cc: list[str]
    assunto: str
    corpo_html: str | None
    modo: str
    status: str
    erro_detalhes: str | None
    boletos_ids: list[uuid.UUID]
    xmls_anexados: list[str]
    timestamp_envio: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnvioStatusUpdate(BaseModel):
    status: str  # "enviado"


# ── Preview envio schemas ────────────────────────────────────


class PreviewEnvioGrupo(BaseModel):
    email_para: list[str]
    email_cc: list[str]
    assunto: str
    corpo_html: str
    boletos: list[BoletoCompleto]
    xmls: list[XmlResumo]


class PreviewEnvioResponse(BaseModel):
    total_grupos: int
    total_aprovados: int
    grupos: list[PreviewEnvioGrupo]


# ── Valores agregados (Explorer) schemas ─────────────────


class ValoresAgregadoItem(BaseModel):
    periodo: str
    periodo_label: str
    valor_bruto: float
    valor_liquido: float
    count: int


class ValoresAgregadoResponse(BaseModel):
    items: list[ValoresAgregadoItem]
    total_bruto: float
    total_liquido: float
    total_operacoes: int


# ── Atividade (audit trail) schemas ────────────────────────


class AtividadeItem(BaseModel):
    id: int
    acao: str
    acao_label: str
    usuario_nome: str | None = None
    detalhes: dict | None = None
    created_at: datetime


class AtividadeResponse(BaseModel):
    items: list[AtividadeItem]
    total: int


