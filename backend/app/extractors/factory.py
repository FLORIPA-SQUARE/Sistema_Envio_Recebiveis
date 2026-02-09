"""
Factory Pattern para seleção de extrator por FIDC.

Seleciona o extrator correto baseado em palavras-chave detectadas
no texto do boleto PDF ou pelo FIDC escolhido na operação.
"""

from app.extractors.base import BaseExtractor
from app.extractors.capital import CapitalExtractor
from app.extractors.credvale import CredvaleExtractor
from app.extractors.novax import NovaxExtractor
from app.extractors.squid import SquidExtractor

# Mapa de palavras-chave → extrator (ordem importa: mais específico primeiro)
_KEYWORD_MAP: list[tuple[list[str], type[BaseExtractor]]] = [
    (["CAPITAL RS", "CAPITAL RS FIDC"], CapitalExtractor),
    (["NOVAX"], NovaxExtractor),
    (["CREDVALE", "CREDIT VALLEY"], CredvaleExtractor),
    (["SQUID"], SquidExtractor),
]

# Mapa direto nome → classe
_FIDC_MAP: dict[str, type[BaseExtractor]] = {
    "CAPITAL": CapitalExtractor,
    "NOVAX": NovaxExtractor,
    "CREDVALE": CredvaleExtractor,
    "SQUID": SquidExtractor,
}


def get_extractor_by_name(nome_fidc: str) -> BaseExtractor:
    """Retorna o extrator pelo nome do FIDC.

    Args:
        nome_fidc: Nome do FIDC (CAPITAL, NOVAX, CREDVALE, SQUID)

    Raises:
        ValueError: Se FIDC não é reconhecido
    """
    nome_upper = nome_fidc.upper().strip()
    cls = _FIDC_MAP.get(nome_upper)
    if cls is None:
        raise ValueError(
            f"FIDC '{nome_fidc}' não reconhecido. "
            f"Disponíveis: {list(_FIDC_MAP.keys())}"
        )
    return cls()


def detect_fidc_from_text(texto: str) -> BaseExtractor | None:
    """Detecta o FIDC automaticamente pelo texto do boleto.

    Busca palavras-chave no texto (case-insensitive).
    Retorna None se nenhum FIDC detectado.
    """
    texto_upper = texto.upper()
    for keywords, cls in _KEYWORD_MAP:
        for kw in keywords:
            if kw.upper() in texto_upper:
                return cls()
    return None


def get_all_extractors() -> dict[str, BaseExtractor]:
    """Retorna dicionário com todos os extratores disponíveis."""
    return {name: cls() for name, cls in _FIDC_MAP.items()}
