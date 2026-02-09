"""
Extrator CREDVALE — Formato boleto tradicional.

Regex e lógica replicados exatamente do legado (extratores-por-fidc.mdx).
Peculiaridades:
  - Linha exata "Pagador" (sem dois-pontos)
  - Pode ter "- EPP -" antes do CNPJ (sem label "CNPJ")
  - Validação: próxima linha não pode ser código de barras
"""

import re

from app.extractors.base import BaseExtractor, DadosBoleto


class CredvaleExtractor(BaseExtractor):
    nome_fidc = "CREDVALE"

    def extrair(self, texto: str, nome_arquivo: str = "") -> DadosBoleto:
        linhas = texto.split("\n")
        dados = DadosBoleto(fidc_detectada=self.nome_fidc)

        dados.pagador = self._extrair_pagador(texto, linhas)
        dados.vencimento, dados.vencimento_completo = self.extrair_vencimento(texto)
        dados.numero_nota = self._extrair_numero_nota(linhas)
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
        # Prioridade 1: Linha exata "Pagador" (sem dois-pontos)
        for i, linha in enumerate(linhas):
            if linha.strip() == "Pagador":
                if i + 1 < len(linhas):
                    linha_pagador = linhas[i + 1].strip()
                    # Validação: não pode ser linha de código de barras
                    if not re.match(r"^\d{5}\.\d{5}\s+\d{5}", linha_pagador) and linha_pagador:
                        return self.limpar_nome(linha_pagador)

        # Prioridade 2: Regex multiline com "- EPP -"
        match = re.search(
            r"Pagador\s*\n\s*([A-ZÀ-Ú][A-ZÀ-Ú\s.\-&]+?)\s*-\s*(?:CNPJ|CPF)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return self.limpar_nome(match.group(1).strip())

        # Prioridade 3: Texto compacto (fallback Novax-style)
        compacto = re.sub(r"\s+", " ", texto).strip()
        match = re.search(
            r"Pagador:\s*([A-Z0-9][A-Z0-9\s.\-&]+?)(?:\s+CNPJ[/\s]|\s+CPF)",
            compacto,
            re.IGNORECASE,
        )
        if match:
            return self.limpar_nome(match.group(1).strip())

        # Prioridade 4: "PAGADOR" genérico
        for i, linha in enumerate(linhas):
            if "PAGADOR" in linha.upper():
                if i + 1 < len(linhas):
                    nome = linhas[i + 1].strip()
                    if nome and not re.match(r"^\d{5}\.\d{5}", nome):
                        return self.limpar_nome(nome)

        return None

    def _extrair_valor(self, texto: str) -> str | None:
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

    def _extrair_numero_nota(self, linhas: list[str]) -> str | None:
        # Credvale: Número do Documento
        nota = self.extrair_numero_documento(linhas)
        if nota:
            return nota
        return None

    def _extrair_cnpj(self, texto: str, linhas: list[str]) -> str | None:
        # Busca na vizinhança de "Pagador" (exato) ou "PAGADOR"
        for i, linha in enumerate(linhas):
            if linha.strip() == "Pagador" or "PAGADOR" in linha.upper():
                cnpj = self.extrair_cnpj_cpf(
                    "", linhas, inicio=i, fim=min(i + 5, len(linhas))
                )
                if cnpj:
                    return cnpj

        # Fallback: "- EPP -" pode ter CNPJ direto sem label
        match = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto)
        if match:
            return match.group(1)

        return None
