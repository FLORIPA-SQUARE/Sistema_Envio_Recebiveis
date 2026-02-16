"""
Email Template Builder — gera HTML do corpo do email e assunto.

Template conforme PRD RF-008.
"""

from datetime import datetime


def _saudacao_por_horario() -> str:
    """Retorna saudacao automatica conforme hora do dia.

    Bom dia (0h-12h), Boa tarde (13h-18h), Boa noite (19h-23h).
    """
    hora = datetime.now().hour
    if hora <= 12:
        return "Bom dia,"
    elif hora <= 18:
        return "Boa tarde,"
    else:
        return "Boa noite,"


def gerar_assunto(numeros_nf: list[str]) -> str:
    """Gera assunto do email no formato: 'Boleto e Nota Fiscal (NF1, NF2, NF3)'."""
    nfs = ", ".join(numeros_nf)
    return f"Boleto e Nota Fiscal ({nfs})"


def gerar_email_html(
    nome_cliente: str,
    boletos_info: list[dict],
    nome_fidc_completo: str,
    cnpj_fidc: str,
    saudacao: str | None = None,
    introducao: str = "Prezado cliente,",
    mensagem_fechamento: str = "Em caso de duvidas, nossa equipe permanece a disposicao para esclarecimentos.",
    assinatura_nome: str = "Equipe de Cobranca",
) -> str:
    """Gera corpo HTML do email conforme template do PRD.

    Args:
        nome_cliente: Nome do destinatario (ex: "EMPRESA XYZ LTDA")
        boletos_info: Lista de dicts com keys: numero_nota, valor_formatado, vencimento_completo
        nome_fidc_completo: Nome completo do FIDC beneficiario
        cnpj_fidc: CNPJ do FIDC formatado
        saudacao: Saudacao inicial — se None, usa automatica por horario
        introducao: Introducao antes do nome (ex: "Prezado cliente,")
        mensagem_fechamento: Mensagem de fechamento
        assinatura_nome: Nome da assinatura (ex: "Equipe de Cobranca")
    """
    if saudacao is None:
        saudacao = _saudacao_por_horario()

    # Lista de NFs
    nfs_lista = ", ".join(b["numero_nota"] for b in boletos_info if b.get("numero_nota"))

    # Linhas de valor/vencimento
    linhas_valores = ""
    for b in boletos_info:
        valor = b.get("valor_formatado", "N/A")
        vencimento = b.get("vencimento_completo", b.get("vencimento", "N/A"))
        linhas_valores += f"<p>Valor: {valor}, Vencimento: {vencimento}</p>\n"

    # Pluralizacao
    qtd = len(boletos_info)
    boleto_s = "boleto" if qtd == 1 else "boletos"
    nota_s = "nota" if qtd == 1 else "notas"
    esta_ao = "esta" if qtd == 1 else "estao"
    emitido_s = "emitido" if qtd == 1 else "emitidos"

    html = f"""<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>{saudacao}</p>

<p>{introducao}<br>
<strong>{nome_cliente}</strong>,</p>

<p>Enviamos anexo o(s) seu(s) {boleto_s} {emitido_s} conforme a(s) {nota_s}: <strong>{nfs_lista}</strong></p>

{linhas_valores}

<p>O(s) {boleto_s} {esta_ao} com beneficiario nominal a <strong>{nome_fidc_completo}</strong>, CNPJ: <strong>{cnpj_fidc}</strong>.</p>

<p>Vide {boleto_s} e {nota_s} em anexo.<br>
Favor confirmar recebimento.</p>

<p>{mensagem_fechamento}</p>

<p>Atenciosamente,<br>
<strong>{assinatura_nome}</strong></p>
<img src="cid:assinatura_jj" alt="JotaJota - Eletrica, Hidraulica, Iluminacao" style="max-width: 500px; height: auto;" />
</body>
</html>"""

    return html
