"""
Extrator SQUID — Formato DANFE (similar ao Capital RS) + Boleto tradicional.

Regex e lógica replicados exatamente do legado (extratores-por-fidc.mdx).
Peculiaridades:
  - Seção FATURA: formato ligeiramente diferente do Capital RS
  - Bug v2.0 corrigido: regex captura APENAS valor, não concatena com dia
  - Número da NF pode vir do nome do arquivo (ex: "3-0305537.pdf")
"""

import os
import re

from app.extractors.base import BaseExtractor, DadosBoleto


class SquidExtractor(BaseExtractor):
    nome_fidc = "SQUID"

    def extrair(self, texto: str, nome_arquivo: str = "") -> DadosBoleto:
        linhas = texto.split("\n")
        dados = DadosBoleto(fidc_detectada=self.nome_fidc)

        dados.pagador = self._extrair_pagador(texto, linhas)
        dados.vencimento, dados.vencimento_completo = self.extrair_vencimento(texto)
        dados.numero_nota = self._extrair_numero_nota(linhas, nome_arquivo)
        dados.cnpj = self._extrair_cnpj(texto, linhas)

        valor_str = self._extrair_valor(texto)
        dados.valor, dados.valor_formatado = self.formatar_valor(valor_str)

        if not dados.pagador:
            dados.erros.append("Pagador não encontrado")
        if not dados.vencimento:
            dados.vencimento = "A definir"
            dados.erros.append("Data de vencimento não encontrada")
        if dados.valor is None:
            dados.erros.append("Valor não encontrado")
        if not dados.numero_nota:
            dados.erros.append("Número da nota não encontrado")

        return dados

    def _extrair_pagador(self, texto: str, linhas: list[str]) -> str | None:
        # Prioridade 1: DANFE — DESTINATÁRIO/REMETENTE (idêntico ao Capital RS)
        for i, linha in enumerate(linhas):
            if "DESTINAT" in linha.upper() and "REMETENTE" in linha.upper():
                if i + 2 < len(linhas):
                    linha_nome = linhas[i + 2].strip()
                    if "CNPJ" not in linha_nome.upper() and "CPF" not in linha_nome.upper() and linha_nome:
                        return self.limpar_nome(linha_nome)

        # Prioridade 2: Boleto tradicional — "PAGADOR"
        for i, linha in enumerate(linhas):
            if "PAGADOR" in linha.upper():
                if i + 1 < len(linhas):
                    nome = linhas[i + 1].strip()
                    if nome:
                        return self.limpar_nome(nome)

        # Prioridade 3: Texto compacto (fallback)
        compacto = re.sub(r"\s+", " ", texto).strip()
        match = re.search(
            r"Pagador:\s*([A-Z0-9][A-Z0-9\s.\-&]+?)(?:\s+CNPJ[/\s]|\s+CPF)",
            compacto,
            re.IGNORECASE,
        )
        if match:
            return self.limpar_nome(match.group(1).strip())

        return None

    def _extrair_valor(self, texto: str) -> str | None:
        # Prioridade 0: Seção FATURA SQUID (HIGHEST PRIORITY)
        # Bug fix v2.0: captura APENAS valor, não concatena com dia
        valor = self.extrair_valor_fatura(texto)
        if valor:
            return valor

        # Prioridade 1: Valor do Documento
        valor = self.extrair_valor_documento(texto)
        if valor:
            return valor

        # Prioridade 2: Linha data + valor
        valor = self.extrair_valor_data_linha(texto)
        if valor:
            return valor

        # Prioridade 3: R$ genérico
        match = re.search(r"R\$\s*([\d.,]+)", texto)
        if match:
            return match.group(1)

        # Prioridade 4: Código de barras
        valor = self.extrair_valor_barcode(texto)
        if valor:
            return valor

        return None

    def _extrair_numero_nota(self, linhas: list[str], nome_arquivo: str) -> str | None:
        # Prioridade 1: DANFE — NÚMERO DA NOTA
        nota = self.extrair_numero_nota_danfe(linhas)
        if nota:
            return nota

        # Prioridade 2: Boleto — Número do Documento
        nota = self.extrair_numero_documento(linhas)
        if nota:
            return nota

        # Prioridade 3: Extrair do nome do arquivo (Squid-specific)
        if nome_arquivo:
            nota = self._extrair_nf_do_filename(nome_arquivo)
            if nota:
                return nota

        return None

    @staticmethod
    def _extrair_nf_do_filename(filename: str) -> str | None:
        """Extrai NF do nome do arquivo (Squid-specific).

        Exemplos:
            "3-0305537.pdf" → "305537"
            "305537.pdf" → "305537"
        """
        nome_arq = os.path.basename(filename)

        # Pattern 1: "3-0305537.pdf" (com prefixo)
        match = re.search(r"\d+-0?(\d{6})\.", nome_arq)
        if match:
            return match.group(1)

        # Pattern 2: "305537.pdf" (sem prefixo)
        match = re.search(r"^0?(\d{6})\.", nome_arq)
        if match:
            return match.group(1)

        return None

    def _extrair_cnpj(self, texto: str, linhas: list[str]) -> str | None:
        # Busca na vizinhança de DESTINATÁRIO/REMETENTE
        for i, linha in enumerate(linhas):
            if "DESTINAT" in linha.upper() and "REMETENTE" in linha.upper():
                cnpj = self.extrair_cnpj_cpf(
                    "", linhas, inicio=i + 1, fim=min(i + 6, len(linhas))
                )
                if cnpj:
                    return cnpj

        # Fallback: vizinhança de PAGADOR
        for i, linha in enumerate(linhas):
            if "PAGADOR" in linha.upper():
                cnpj = self.extrair_cnpj_cpf(
                    "", linhas, inicio=i, fim=min(i + 5, len(linhas))
                )
                if cnpj:
                    return cnpj

        return None
