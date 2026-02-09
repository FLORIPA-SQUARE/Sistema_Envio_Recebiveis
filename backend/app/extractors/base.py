"""
Base extractor with shared helpers used by all FIDC extractors.

All regex patterns and extraction algorithms are replicated exactly
from the legacy system as documented in docs/legacy_mintlify/extratores-por-fidc.mdx.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DadosBoleto:
    """Dados extraídos de um boleto PDF."""

    pagador: str | None = None
    cnpj: str | None = None
    numero_nota: str | None = None
    vencimento: str | None = None  # DD-MM
    vencimento_completo: str | None = None  # DD/MM/YYYY
    valor: float | None = None
    valor_formatado: str | None = None  # R$ X.XXX,XX
    fidc_detectada: str | None = None
    erros: list[str] = field(default_factory=list)


class BaseExtractor(ABC):
    """Classe base para todos os extratores de FIDC."""

    nome_fidc: str = ""

    @abstractmethod
    def extrair(self, texto: str, nome_arquivo: str = "") -> DadosBoleto:
        """Extrai dados do texto de um boleto PDF."""
        ...

    # ── Helpers compartilhados ──────────────────────────────────

    @staticmethod
    def limpar_nome(nome: str) -> str:
        """Remove CNPJ/CPF e caracteres indesejados do nome do pagador.

        Replica exatamente _limpar_nome() do legado:
        - Split em vírgula, "CNPJ" ou "CPF"
        - Pega apenas a primeira parte
        - Strip whitespace
        """
        if not nome:
            return ""
        nome = re.split(r",|CNPJ|CPF", nome, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        # Remove caracteres ilegais para nomes de arquivo Windows
        nome = re.sub(r'[\\/:*?"<>|]', "", nome)
        return nome.strip()

    @staticmethod
    def extrair_vencimento(texto: str) -> tuple[str | None, str | None]:
        """Extrai vencimento do boleto.

        Returns:
            (vencimento_ddmm, vencimento_completo) — ex: ("13-01", "13/01/2026")
        """
        linhas = texto.split("\n")
        for linha in linhas:
            if "VENCIMENTO" in linha.upper():
                match = re.search(r"(\d{2})/(\d{2})/(\d{4})", linha)
                if match:
                    dd, mm, yyyy = match.group(1), match.group(2), match.group(3)
                    return f"{dd}-{mm}", f"{dd}/{mm}/{yyyy}"

        # Fallback: procurar qualquer data DD/MM/YYYY no texto todo
        match = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto)
        if match:
            dd, mm, yyyy = match.group(1), match.group(2), match.group(3)
            return f"{dd}-{mm}", f"{dd}/{mm}/{yyyy}"

        return None, None

    @staticmethod
    def extrair_cnpj_cpf(texto: str, linhas: list[str], inicio: int = 0, fim: int | None = None) -> str | None:
        """Extrai CNPJ ou CPF de um trecho de linhas.

        Prioridade: CNPJ > CPF
        """
        if fim is None:
            fim = min(inicio + 5, len(linhas))
        for j in range(inicio, fim):
            match_cnpj = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", linhas[j])
            if match_cnpj:
                return match_cnpj.group(1)
            match_cpf = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", linhas[j])
            if match_cpf:
                return match_cpf.group(1)
        return None

    @staticmethod
    def extrair_valor_documento(texto: str) -> str | None:
        """Extrai valor usando padrão 'Valor do Documento'.

        Pattern 1: (=) Valor Documento
        Pattern 2: Valor Documento (sem (=))
        """
        # Pattern 1: com (=)
        match = re.search(
            r"\(=\)\s*Valor\s+(?:do\s+)?Documento\s*[:\s]*(?:R\$\s*)?([\d.,]+)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return match.group(1)

        # Pattern 2: sem (=)
        match = re.search(
            r"Valor\s+(?:do\s+)?Documento\s*[:\s]*(?:R\$\s*)?([\d.,]+)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return match.group(1)

        return None

    @staticmethod
    def extrair_valor_data_linha(texto: str) -> str | None:
        """Extrai valor do padrão 'numero_doc data valor'.

        Pattern: 310926/004 17/02/2026 2.221,20
        """
        match = re.search(r"\d{6}[/\d]*\s+\d{2}/\d{2}/\d{4}\s+([\d.,]+)", texto)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def extrair_valor_barcode(texto: str) -> str | None:
        """Extrai valor do código de barras (último recurso).

        Posições 3-13 do código de 14 dígitos contêm o valor em centavos.
        """
        match = re.search(
            r"\d{5}\.\d{5}\s+\d{5}\.\d{6}\s+\d{5}\.\d{6}\s+\d\s+(\d{14})",
            texto,
        )
        if match:
            codigo = match.group(1)
            valor_cents = int(codigo[3:13])
            if valor_cents > 0:
                valor_reais = valor_cents / 100
                return f"{valor_reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return None

    @staticmethod
    def extrair_valor_fatura(texto: str) -> str | None:
        """Extrai valor da seção FATURA (DANFE).

        Pattern: FATURA ... \\n ... \\n NNN DD/MM/YYYY VALOR
        Captura APENAS o valor, não o dia (bug fix v2.0).
        """
        match = re.search(
            r"FATURA.*?[\r\n]+.*?[\r\n]+\s*\d{3}\s+\d{2}/\d{2}/\d{4}\s+(\d{1,3}(?:\.\d{3})*,\d{2})(?:\s|$)",
            texto,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1)
        return None

    @staticmethod
    def extrair_numero_documento(linhas: list[str]) -> str | None:
        """Extrai 'Número do Documento' (padrão boleto tradicional).

        Remove sufixo /001 e zero à esquerda.
        """
        for i, linha in enumerate(linhas):
            if "MERO DO DOCUMENTO" in linha.upper():
                for j in range(i, min(i + 4, len(linhas))):
                    match = re.search(r"0?(\d{6})(?:/\d{3})?", linhas[j])
                    if match:
                        return match.group(1)
        return None

    @staticmethod
    def extrair_numero_nota_danfe(linhas: list[str]) -> str | None:
        """Extrai 'NÚMERO DA NOTA' (padrão DANFE)."""
        for i, linha in enumerate(linhas):
            if "MERO DA NOTA" in linha.upper():
                for j in range(i, min(i + 4, len(linhas))):
                    match = re.search(r"0?(\d{6})", linhas[j])
                    if match:
                        return match.group(1)
        return None

    @staticmethod
    def formatar_valor(valor_str: str | None) -> tuple[float | None, str | None]:
        """Converte string de valor para float e formato R$ X.XXX,XX.

        Aceita: "2.833,34" / "2833.34" / "2833,34"
        Retorna: (2833.34, "R$ 2.833,34")
        """
        if not valor_str:
            return None, None

        # Limpa prefixo R$
        limpo = valor_str.replace("R$", "").strip()

        # Detecta formato brasileiro (ponto como milhar, vírgula como decimal)
        if "," in limpo:
            limpo = limpo.replace(".", "")  # Remove separador de milhar
            limpo = limpo.replace(",", ".")  # Vírgula → ponto decimal
        # Se não tem vírgula, assume formato com ponto decimal

        try:
            valor_float = float(limpo)
        except ValueError:
            return None, None

        # Formata para pt-BR
        inteiro = int(valor_float)
        centavos = round((valor_float - inteiro) * 100)
        parte_inteira = f"{inteiro:,}".replace(",", ".")
        formatado = f"R$ {parte_inteira},{centavos:02d}"

        return valor_float, formatado
