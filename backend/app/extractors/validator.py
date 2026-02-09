"""
Validação em 5 Camadas — compara dados do boleto PDF vs XML NFe.

Replicado exatamente do legado conforme docs/legacy_mintlify:
  - Camada 1: XML existe e é válido
  - Camada 2: CNPJ do boleto == CNPJ do XML (14 dígitos exatos)
  - Camada 3: Nome fuzzy matching >= 85% (SequenceMatcher)
  - Camada 4: Valor com tolerância ZERO (0 centavos)
  - Camada 5: >= 1 email válido encontrado

Tolerância de valor: ZERO (configurável se necessário).
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.extractors.base import DadosBoleto
from app.extractors.xml_parser import DadosXmlNfe

# Constantes do legado
TOLERANCIA_VALOR_CENTAVOS = 0
SIMILARIDADE_MINIMA = 0.85
MAX_EMAILS_POR_CLIENTE = 2


@dataclass
class ResultadoCamada:
    """Resultado de uma camada de validação."""

    camada: int
    nome: str
    aprovado: bool
    mensagem: str
    bloqueia: bool = False  # True = rejeita o boleto
    detalhes: dict = field(default_factory=dict)


@dataclass
class ResultadoValidacao:
    """Resultado completo da validação de 5 camadas."""

    aprovado: bool = True
    motivo_rejeicao: str | None = None
    camadas: list[ResultadoCamada] = field(default_factory=list)
    juros_detectado: bool = False
    juros_detalhes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "aprovado": self.aprovado,
            "motivo_rejeicao": self.motivo_rejeicao,
            "juros_detectado": self.juros_detectado,
            "juros_detalhes": self.juros_detalhes,
            "camadas": [
                {
                    "camada": c.camada,
                    "nome": c.nome,
                    "aprovado": c.aprovado,
                    "mensagem": c.mensagem,
                    "bloqueia": c.bloqueia,
                    "detalhes": c.detalhes,
                }
                for c in self.camadas
            ],
        }


def validar_5_camadas(
    dados_boleto: DadosBoleto,
    dados_xml: DadosXmlNfe | None,
) -> ResultadoValidacao:
    """Executa a validação completa em 5 camadas."""
    resultado = ResultadoValidacao()

    # ── Camada 1: XML ─────────────────────────────────────────
    c1 = _validar_camada1_xml(dados_boleto, dados_xml)
    resultado.camadas.append(c1)
    if c1.bloqueia:
        resultado.aprovado = False
        resultado.motivo_rejeicao = c1.mensagem
        # Se não tem XML, não faz sentido continuar
        _preencher_camadas_restantes(resultado, a_partir_de=2)
        return resultado

    # A partir daqui, dados_xml é garantidamente não-None
    assert dados_xml is not None

    # ── Camada 2: CNPJ ────────────────────────────────────────
    c2 = _validar_camada2_cnpj(dados_boleto, dados_xml)
    resultado.camadas.append(c2)
    if c2.bloqueia:
        resultado.aprovado = False
        resultado.motivo_rejeicao = c2.mensagem

    # ── Camada 3: Nome (fuzzy) ────────────────────────────────
    c3 = _validar_camada3_nome(dados_boleto, dados_xml)
    resultado.camadas.append(c3)
    # Camada 3 NUNCA bloqueia (apenas warning)

    # ── Camada 4: Valor (zero tolerance) ──────────────────────
    c4 = _validar_camada4_valor(dados_boleto, dados_xml)
    resultado.camadas.append(c4)
    if c4.bloqueia:
        resultado.aprovado = False
        resultado.motivo_rejeicao = c4.mensagem

    # Detecção de juros/multa
    juros = _detectar_juros_multa(dados_boleto, dados_xml)
    resultado.juros_detectado = juros["tem_juros_multa"]
    resultado.juros_detalhes = juros

    # ── Camada 5: Email ───────────────────────────────────────
    c5 = _validar_camada5_email(dados_xml)
    resultado.camadas.append(c5)
    if c5.bloqueia:
        resultado.aprovado = False
        resultado.motivo_rejeicao = c5.mensagem

    return resultado


# ── Implementação de cada camada ──────────────────────────────


def _validar_camada1_xml(
    dados_boleto: DadosBoleto, dados_xml: DadosXmlNfe | None
) -> ResultadoCamada:
    """Camada 1: XML existe + válido + número da nota confere."""
    if dados_xml is None:
        return ResultadoCamada(
            camada=1,
            nome="XML",
            aprovado=False,
            mensagem=f"XML não encontrado para nota {dados_boleto.numero_nota or '?'}",
            bloqueia=True,
        )

    if not dados_xml.xml_valido:
        return ResultadoCamada(
            camada=1,
            nome="XML",
            aprovado=False,
            mensagem=f"XML inválido: {dados_xml.erro or 'erro desconhecido'}",
            bloqueia=True,
        )

    # Compara número da nota (remove zeros à esquerda)
    nf_boleto = (dados_boleto.numero_nota or "").lstrip("0")
    nf_xml = (dados_xml.numero_nota or "").lstrip("0")

    if nf_boleto and nf_xml and nf_boleto != nf_xml:
        return ResultadoCamada(
            camada=1,
            nome="XML",
            aprovado=False,
            mensagem=f"Número da nota divergente: boleto={nf_boleto}, XML={nf_xml}",
            bloqueia=True,
            detalhes={"nf_boleto": nf_boleto, "nf_xml": nf_xml},
        )

    return ResultadoCamada(
        camada=1,
        nome="XML",
        aprovado=True,
        mensagem="XML válido e número da nota confere",
        detalhes={"numero_nota": nf_xml},
    )


def _validar_camada2_cnpj(dados_boleto: DadosBoleto, dados_xml: DadosXmlNfe) -> ResultadoCamada:
    """Camada 2: CNPJ do boleto == CNPJ do XML (14 dígitos exatos)."""
    cnpj_boleto = _limpar_cnpj(dados_boleto.cnpj or "")
    cnpj_xml = _limpar_cnpj(dados_xml.cnpj or "")

    if not cnpj_boleto or not cnpj_xml:
        return ResultadoCamada(
            camada=2,
            nome="CNPJ",
            aprovado=True,
            mensagem="CNPJ não disponível para comparação",
            detalhes={"cnpj_boleto": cnpj_boleto, "cnpj_xml": cnpj_xml},
        )

    if cnpj_boleto == cnpj_xml:
        return ResultadoCamada(
            camada=2,
            nome="CNPJ",
            aprovado=True,
            mensagem="CNPJ confere",
            detalhes={"cnpj": cnpj_boleto},
        )

    return ResultadoCamada(
        camada=2,
        nome="CNPJ",
        aprovado=False,
        mensagem=f"CNPJ divergente! Boleto={cnpj_boleto}, XML={cnpj_xml}",
        bloqueia=True,
        detalhes={"cnpj_boleto": cnpj_boleto, "cnpj_xml": cnpj_xml},
    )


def _validar_camada3_nome(dados_boleto: DadosBoleto, dados_xml: DadosXmlNfe) -> ResultadoCamada:
    """Camada 3: Nome fuzzy matching >= 85% (SequenceMatcher).

    NUNCA bloqueia — apenas warning.
    """
    nome_boleto = _normalizar_nome(dados_boleto.pagador or "")
    nome_xml = _normalizar_nome(dados_xml.nome_destinatario or "")

    if not nome_boleto or not nome_xml:
        return ResultadoCamada(
            camada=3,
            nome="Nome",
            aprovado=True,
            mensagem="Nome não disponível para comparação",
            detalhes={"nome_boleto": nome_boleto, "nome_xml": nome_xml},
        )

    similaridade = SequenceMatcher(None, nome_boleto, nome_xml).ratio()
    pct = round(similaridade * 100, 1)

    if similaridade >= SIMILARIDADE_MINIMA:
        return ResultadoCamada(
            camada=3,
            nome="Nome",
            aprovado=True,
            mensagem=f"Similaridade {pct}% (>={SIMILARIDADE_MINIMA * 100:.0f}%)",
            detalhes={"similaridade": pct, "nome_boleto": nome_boleto, "nome_xml": nome_xml},
        )

    return ResultadoCamada(
        camada=3,
        nome="Nome",
        aprovado=False,
        mensagem=f"Similaridade baixa ({pct}%)",
        bloqueia=False,  # NUNCA bloqueia
        detalhes={"similaridade": pct, "nome_boleto": nome_boleto, "nome_xml": nome_xml},
    )


def _validar_camada4_valor(dados_boleto: DadosBoleto, dados_xml: DadosXmlNfe) -> ResultadoCamada:
    """Camada 4: Valor com tolerância ZERO.

    Prioridade: valor da duplicata (se vencimento confere) > valor total.
    """
    valor_boleto = dados_boleto.valor
    if valor_boleto is None:
        return ResultadoCamada(
            camada=4,
            nome="Valor",
            aprovado=True,
            mensagem="Valor do boleto não disponível para comparação",
        )

    # Prioridade: duplicata com vencimento correspondente
    valor_xml = _obter_valor_xml_correspondente(dados_boleto, dados_xml)

    if valor_xml is None or valor_xml == 0:
        return ResultadoCamada(
            camada=4,
            nome="Valor",
            aprovado=True,
            mensagem="Valor do XML não disponível para comparação",
            detalhes={"valor_boleto": valor_boleto},
        )

    # Converte para centavos para comparação exata
    centavos_boleto = round(valor_boleto * 100)
    centavos_xml = round(valor_xml * 100)
    diferenca = abs(centavos_boleto - centavos_xml)

    if diferenca <= TOLERANCIA_VALOR_CENTAVOS:
        return ResultadoCamada(
            camada=4,
            nome="Valor",
            aprovado=True,
            mensagem="Valor confere",
            detalhes={"valor_boleto": valor_boleto, "valor_xml": valor_xml},
        )

    diferenca_reais = diferenca / 100
    return ResultadoCamada(
        camada=4,
        nome="Valor",
        aprovado=False,
        mensagem=f"Valor divergente! Diferença R$ {diferenca_reais:.2f}",
        bloqueia=True,
        detalhes={
            "valor_boleto": valor_boleto,
            "valor_xml": valor_xml,
            "diferenca": diferenca_reais,
        },
    )


def _validar_camada5_email(dados_xml: DadosXmlNfe) -> ResultadoCamada:
    """Camada 5: >= 1 email válido encontrado."""
    emails_validos = dados_xml.emails

    if len(emails_validos) >= 1:
        return ResultadoCamada(
            camada=5,
            nome="Email",
            aprovado=True,
            mensagem=f"{len(emails_validos)} email(s) válido(s)",
            detalhes={"emails": emails_validos, "emails_invalidos": dados_xml.emails_invalidos},
        )

    msg = "Nenhum email válido encontrado"
    if dados_xml.emails_invalidos:
        msg += f" (filtrados: {dados_xml.emails_invalidos})"

    return ResultadoCamada(
        camada=5,
        nome="Email",
        aprovado=False,
        mensagem=msg,
        bloqueia=True,
        detalhes={"emails_invalidos": dados_xml.emails_invalidos},
    )


# ── Helpers internos ──────────────────────────────────────────


def _limpar_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ/CPF, retorna apenas dígitos."""
    return re.sub(r"\D", "", cnpj)


def _normalizar_nome(nome: str) -> str:
    """Normaliza nome para comparação fuzzy: upper, sem acentos, sem pontuação."""
    nome = nome.upper().strip()
    # Remove acentos simples (sem dependência de unidecode)
    acentos = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A", "Ä": "A",
        "É": "E", "È": "E", "Ê": "E", "Ë": "E",
        "Í": "I", "Ì": "I", "Î": "I", "Ï": "I",
        "Ó": "O", "Ò": "O", "Õ": "O", "Ô": "O", "Ö": "O",
        "Ú": "U", "Ù": "U", "Û": "U", "Ü": "U",
        "Ç": "C",
    }
    for ac, sub in acentos.items():
        nome = nome.replace(ac, sub)
    # Remove pontuação
    nome = re.sub(r"[^\w\s]", "", nome)
    # Normaliza espaços
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome


def _obter_valor_xml_correspondente(dados_boleto: DadosBoleto, dados_xml: DadosXmlNfe) -> float | None:
    """Obtém valor do XML correspondente ao boleto.

    Prioridade:
    1. Duplicata com vencimento correspondente
    2. Valor total da NFe
    """
    if dados_xml.duplicatas and dados_boleto.vencimento_completo:
        # Converte vencimento do boleto (DD/MM/YYYY) para YYYY-MM-DD
        venc_boleto = dados_boleto.vencimento_completo
        match = re.match(r"(\d{2})/(\d{2})/(\d{4})", venc_boleto)
        if match:
            dd, mm, yyyy = match.group(1), match.group(2), match.group(3)
            venc_iso = f"{yyyy}-{mm}-{dd}"

            for dup in dados_xml.duplicatas:
                if dup.get("vencimento") == venc_iso:
                    return dup.get("valor", 0.0)

    # Fallback: valor total
    if dados_xml.valor_total > 0:
        return dados_xml.valor_total

    return None


def _detectar_juros_multa(dados_boleto: DadosBoleto, dados_xml: DadosXmlNfe) -> dict:
    """Detecta se boleto inclui juros/multa (RF-014).

    Se valor boleto > valor NF: flag como juros, registra alerta.
    Usa valor NF (original) para filename. NÃO bloqueia envio.
    """
    valor_boleto = dados_boleto.valor
    valor_xml = dados_xml.valor_total

    if valor_boleto is None or valor_xml is None or valor_xml == 0:
        return {"tem_juros_multa": False}

    # Verifica contra duplicata correspondente primeiro
    valor_ref = _obter_valor_xml_correspondente(dados_boleto, dados_xml) or valor_xml

    diferenca = valor_boleto - valor_ref

    if diferenca <= 0:
        return {"tem_juros_multa": False}

    percentual = (diferenca / valor_ref) * 100

    return {
        "tem_juros_multa": True,
        "valor_boleto": valor_boleto,
        "valor_xml": valor_ref,
        "diferenca": round(diferenca, 2),
        "percentual": round(percentual, 2),
    }


def _preencher_camadas_restantes(resultado: ResultadoValidacao, a_partir_de: int) -> None:
    """Preenche camadas não executadas com status 'não validado'."""
    nomes = {2: "CNPJ", 3: "Nome", 4: "Valor", 5: "Email"}
    for i in range(a_partir_de, 6):
        resultado.camadas.append(
            ResultadoCamada(
                camada=i,
                nome=nomes[i],
                aprovado=False,
                mensagem="Não validado (camada anterior falhou)",
            )
        )
