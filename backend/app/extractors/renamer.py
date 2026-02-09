"""
Lógica de renomeação de arquivos de boleto (RF-005).

Formato: {PAGADOR} - NF {NUMERO_NOTA} - {DD-MM} - R$ {VALOR}.pdf
Exemplo: AREAIS DO LESTE SPE LTDA - NF 310227 - 13-01 - R$ 2.833,34.pdf
"""

import re

from app.extractors.base import DadosBoleto


def gerar_nome_arquivo(dados: DadosBoleto) -> str:
    """Gera o nome de arquivo renomeado conforme padrão legado.

    Formato: {PAGADOR} - NF {NUMERO_NOTA} - {DD-MM} - R$ {VALOR}.pdf

    Se campos faltando:
    - pagador: "SEM_PAGADOR"
    - numero_nota: "SEM_NF"
    - vencimento: "A definir"
    - valor: "SEM_VALOR"
    """
    pagador = dados.pagador or "SEM_PAGADOR"
    numero_nota = dados.numero_nota or "SEM_NF"
    vencimento = dados.vencimento or "A definir"
    valor_formatado = dados.valor_formatado or "SEM_VALOR"

    nome = f"{pagador} - NF {numero_nota} - {vencimento} - {valor_formatado}.pdf"

    # Garante que o nome é válido para Windows (max 255 chars)
    nome = _sanitizar_nome_arquivo(nome)

    return nome


def _sanitizar_nome_arquivo(nome: str) -> str:
    """Remove caracteres ilegais para Windows e limita comprimento."""
    # Remove caracteres ilegais (\ / : * ? " < > |) mas mantém R$
    nome = re.sub(r'[\\/:*?"<>|]', "", nome)
    # Substitui múltiplos espaços por um
    nome = re.sub(r"\s+", " ", nome).strip()
    # Limita a 255 caracteres (Windows)
    if len(nome) > 255:
        nome = nome[:251] + ".pdf"
    return nome
