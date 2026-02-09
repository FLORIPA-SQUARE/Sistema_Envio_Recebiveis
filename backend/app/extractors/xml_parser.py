"""
Parser de XML NFe — extrai dados do destinatário, valores e duplicatas.

Replicado do legado (xml_nfe_reader.py) conforme docs/legacy_mintlify.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path


@dataclass
class DadosXmlNfe:
    """Dados extraídos de um arquivo XML NFe."""

    xml_valido: bool = True
    numero_nota: str = ""
    cnpj: str = ""
    nome_destinatario: str = ""
    valor_total: float = 0.0
    emails: list[str] = field(default_factory=list)
    emails_invalidos: list[str] = field(default_factory=list)
    duplicatas: list[dict] = field(default_factory=list)
    dados_raw: dict = field(default_factory=dict)
    nome_arquivo: str = ""
    erro: str | None = None


# Namespace da NFe
_NS = {"nf": "http://www.portalfiscal.inf.br/nfe"}

# Regex para validação de email
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Comprimento máximo do segundo email (legado: 100 chars)
_MAX_EMAIL_2_LEN = 100


def parse_xml_nfe(file_path: str | Path) -> DadosXmlNfe:
    """Faz parse de um arquivo XML NFe e retorna os dados extraídos."""
    file_path = Path(file_path)
    dados = DadosXmlNfe(nome_arquivo=file_path.name)

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError, PermissionError) as e:
        dados.xml_valido = False
        dados.erro = f"Erro ao parsear XML: {e}"
        return dados

    # Tenta encontrar o nó NFe (com ou sem namespace)
    nfe_node = root.find(".//nf:infNFe", _NS)
    if nfe_node is None:
        # Tenta sem namespace
        nfe_node = root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
    if nfe_node is None:
        # Tenta sem namespace nenhum
        nfe_node = root.find(".//infNFe")
    if nfe_node is None:
        # Último recurso: usa root
        nfe_node = root

    # ── Número da nota ────────────────────────────────────────
    dados.numero_nota = _extrair_numero_nota(nfe_node)

    # ── Destinatário ──────────────────────────────────────────
    dest = _find(nfe_node, "dest")
    if dest is not None:
        dados.cnpj = _text(dest, "CNPJ") or _text(dest, "CPF") or ""
        dados.nome_destinatario = _text(dest, "xNome") or ""

        # Emails do destinatário
        email_str = _text(dest, "email") or ""
        if email_str:
            _processar_emails(email_str, dados)

    # ── Valor total ───────────────────────────────────────────
    dados.valor_total = _extrair_valor_total(nfe_node)

    # ── Duplicatas (cobrança) ─────────────────────────────────
    dados.duplicatas = _extrair_duplicatas(nfe_node)

    # ── Dados raw ─────────────────────────────────────────────
    dados.dados_raw = {
        "numero_nota": dados.numero_nota,
        "cnpj": dados.cnpj,
        "nome": dados.nome_destinatario,
        "valor_total": dados.valor_total,
        "emails": dados.emails,
        "duplicatas": dados.duplicatas,
    }

    return dados


def _find(parent: ET.Element, tag: str) -> ET.Element | None:
    """Encontra elemento com ou sem namespace."""
    elem = parent.find(f"nf:{tag}", _NS)
    if elem is None:
        elem = parent.find(f"{{http://www.portalfiscal.inf.br/nfe}}{tag}")
    if elem is None:
        elem = parent.find(tag)
    return elem


def _text(parent: ET.Element, tag: str) -> str | None:
    """Extrai texto de um sub-elemento."""
    elem = _find(parent, tag)
    if elem is not None and elem.text:
        return elem.text.strip()
    return None


def _extrair_numero_nota(nfe_node: ET.Element) -> str:
    """Extrai número da nota do campo <nNF> ou do atributo Id."""
    ide = _find(nfe_node, "ide")
    if ide is not None:
        nnf = _text(ide, "nNF")
        if nnf:
            return nnf.lstrip("0") or "0"

    # Fallback: extrair do atributo Id
    id_attr = nfe_node.get("Id", "")
    match = re.search(r"(\d{6,})", id_attr)
    if match:
        return match.group(1).lstrip("0") or "0"

    return ""


def _extrair_valor_total(nfe_node: ET.Element) -> float:
    """Extrai valor total da NFe (ICMSTot > vNF ou vProd)."""
    total = _find(nfe_node, "total")
    if total is not None:
        icms_tot = _find(total, "ICMSTot")
        if icms_tot is not None:
            # vNF = valor total da nota
            vnf = _text(icms_tot, "vNF")
            if vnf:
                try:
                    return float(Decimal(vnf))
                except (InvalidOperation, ValueError):
                    pass
            # Fallback: vProd
            vprod = _text(icms_tot, "vProd")
            if vprod:
                try:
                    return float(Decimal(vprod))
                except (InvalidOperation, ValueError):
                    pass
    return 0.0


def _extrair_duplicatas(nfe_node: ET.Element) -> list[dict]:
    """Extrai duplicatas da seção <cobr>."""
    duplicatas = []
    cobr = _find(nfe_node, "cobr")
    if cobr is None:
        return duplicatas

    # Busca <dup> com e sem namespace
    dups = cobr.findall("nf:dup", _NS)
    if not dups:
        dups = cobr.findall("{http://www.portalfiscal.inf.br/nfe}dup")
    if not dups:
        dups = cobr.findall("dup")

    for dup in dups:
        ndup = _text(dup, "nDup") or ""
        dvenc = _text(dup, "dVenc") or ""
        vdup = _text(dup, "vDup") or "0"

        try:
            valor = float(Decimal(vdup))
        except (InvalidOperation, ValueError):
            valor = 0.0

        duplicatas.append(
            {
                "numero": ndup,
                "vencimento": dvenc,  # YYYY-MM-DD
                "valor": valor,
            }
        )

    return duplicatas


def _processar_emails(email_str: str, dados: DadosXmlNfe) -> None:
    """Processa string de emails, valida e filtra truncados.

    Regras do legado:
    - Máximo 2 emails válidos
    - 2º email descartado silenciosamente se > 100 chars
    - Emails truncados vão para emails_invalidos
    """
    # Pode vir separado por ; ou , ou espaço
    candidatos = re.split(r"[;,\s]+", email_str.strip())

    for email in candidatos:
        email = email.strip().lower()
        if not email:
            continue

        if _eh_email_truncado(email) or not _EMAIL_RE.match(email):
            dados.emails_invalidos.append(email)
            continue

        if len(dados.emails) == 0:
            dados.emails.append(email)
        elif len(dados.emails) == 1:
            # 2º email: descartar silenciosamente se > 100 chars
            if len(email) <= _MAX_EMAIL_2_LEN:
                dados.emails.append(email)
            else:
                dados.emails_invalidos.append(email)
        # Ignora 3º+ emails


def _eh_email_truncado(email: str) -> bool:
    """Verifica se email está truncado."""
    if email.endswith("."):
        return True
    if email.count("@") != 1:
        return True
    _, domain = email.split("@")
    if not domain or "." not in domain:
        return True
    return False
