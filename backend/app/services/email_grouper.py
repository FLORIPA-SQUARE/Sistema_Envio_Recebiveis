"""
Email Grouper — agrupa boletos aprovados por email destino para envio.

Regras:
- Mesmo email(s) = 1 email com multiplos boletos/XMLs
- Anexos ordenados por vencimento (ascendente)
- CC vem da configuracao do FIDC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.services.email_template import gerar_assunto, gerar_email_html


@dataclass
class EmailGroup:
    """Grupo de email pronto para envio."""

    email_para: list[str]
    email_cc: list[str]
    assunto: str
    corpo_html: str
    boletos_ids: list[str]
    xmls_ids: list[str]
    xmls_nomes: list[str]
    anexos_pdf: list[Path] = field(default_factory=list)
    anexos_xml: list[Path] = field(default_factory=list)


def agrupar_boletos_para_envio(
    boletos_aprovados: list,
    xmls: list,
    fidc,
    storage_base: Path,
    email_layout: dict | None = None,
) -> list[EmailGroup]:
    """Agrupa boletos aprovados por email destino e gera dados de email.

    Args:
        boletos_aprovados: Boleto records com status "aprovado"
        xmls: XmlNfe records da operacao
        fidc: Fidc record (com cc_emails, nome_completo, cnpj)
        storage_base: Path base do storage da operacao (uploads/{op_id})
        email_layout: Dict com campos customizaveis (saudacao, introducao, mensagem_fechamento, assinatura_nome)

    Returns:
        Lista de EmailGroup prontos para SMTPMailer
    """
    # Mapa de XMLs por ID
    xmls_map = {str(x.id): x for x in xmls}

    # Mapa de NF PDFs por numero_nota normalizado (para anexar ao email)
    nf_pdfs_by_nota: dict[str, object] = {}
    for x in xmls:
        if x.nome_arquivo.lower().endswith(".pdf"):
            nf_key = (x.numero_nota or "").lstrip("0") or "0"
            nf_pdfs_by_nota[nf_key] = x

    # Agrupar boletos por chave de email (tupla ordenada dos emails destino)
    grupos: dict[tuple[str, ...], list] = {}

    for boleto in boletos_aprovados:
        # Buscar emails do XML vinculado
        xml = xmls_map.get(str(boleto.xml_nfe_id)) if boleto.xml_nfe_id else None
        emails = xml.emails if xml and xml.emails else []

        if not emails:
            continue  # Sem email, nao pode enviar

        email_key = tuple(sorted(emails))
        if email_key not in grupos:
            grupos[email_key] = []
        grupos[email_key].append((boleto, xml))

    # Converter cada grupo em EmailGroup
    result: list[EmailGroup] = []

    for email_key, boleto_xml_pairs in grupos.items():
        # Ordenar por vencimento ascendente
        boleto_xml_pairs.sort(key=lambda pair: _sort_vencimento(pair[0]))

        boletos_ids = []
        xmls_ids_set = set()
        xmls_nomes = []
        numeros_nf = []
        boletos_info = []
        anexos_pdf = []
        anexos_xml_set: dict[str, Path] = {}

        nome_cliente = None

        for boleto, xml in boleto_xml_pairs:
            boletos_ids.append(str(boleto.id))

            if boleto.numero_nota:
                numeros_nf.append(boleto.numero_nota)

            # Info para template
            vencimento_completo = ""
            if boleto.vencimento:
                # DD-MM -> DD/MM (formato para email)
                parts = boleto.vencimento.split("-")
                if len(parts) == 2:
                    vencimento_completo = f"{parts[0]}/{parts[1]}/2026"

            boletos_info.append({
                "numero_nota": boleto.numero_nota or "N/A",
                "valor_formatado": boleto.valor_formatado or "N/A",
                "vencimento_completo": vencimento_completo,
            })

            # Anexo PDF
            if boleto.arquivo_path:
                pdf_path = Path(boleto.arquivo_path)
                # Se renomeado, usar nome renomeado
                if boleto.arquivo_renomeado:
                    renamed = pdf_path.parent / boleto.arquivo_renomeado
                    if renamed.exists():
                        pdf_path = renamed
                if pdf_path.exists():
                    anexos_pdf.append(pdf_path)

            # Nota fiscal em PDF correspondente (XML nunca e anexado — serve apenas para dados)
            if xml and str(xml.id) not in xmls_ids_set:
                xmls_ids_set.add(str(xml.id))
                xmls_nomes.append(xml.nome_arquivo)
                nf_dir = storage_base / "xmls"
                nf_key = (xml.numero_nota or "").lstrip("0") or "0"
                nf_pdf_record = nf_pdfs_by_nota.get(nf_key)
                if nf_pdf_record:
                    nf_pdf_path = nf_dir / nf_pdf_record.nome_arquivo
                    if nf_pdf_path.exists():
                        anexos_xml_set[str(xml.id)] = nf_pdf_path

            # Nome do cliente (usar do XML se disponivel)
            if not nome_cliente:
                if xml and xml.nome_destinatario:
                    nome_cliente = xml.nome_destinatario
                elif boleto.pagador:
                    nome_cliente = boleto.pagador

        # Gerar assunto e corpo
        assunto = gerar_assunto(numeros_nf)
        layout_kwargs = {}
        if email_layout:
            for k in ("introducao", "mensagem_fechamento", "assinatura_nome"):
                if k in email_layout and email_layout[k]:
                    layout_kwargs[k] = email_layout[k]
        corpo_html = gerar_email_html(
            nome_cliente=nome_cliente or "Cliente",
            boletos_info=boletos_info,
            nome_fidc_completo=fidc.nome_completo,
            cnpj_fidc=fidc.cnpj or "",
            **layout_kwargs,
        )

        result.append(EmailGroup(
            email_para=list(email_key),
            email_cc=fidc.cc_emails or [],
            assunto=assunto,
            corpo_html=corpo_html,
            boletos_ids=boletos_ids,
            xmls_ids=list(xmls_ids_set),
            xmls_nomes=xmls_nomes,
            anexos_pdf=anexos_pdf,
            anexos_xml=list(anexos_xml_set.values()),
        ))

    return result


def _sort_vencimento(boleto) -> str:
    """Chave de ordenacao por vencimento. Formato DD-MM."""
    v = boleto.vencimento or "99-99"
    # Inverter DD-MM para MM-DD para ordenacao correta
    parts = v.split("-")
    if len(parts) == 2:
        return f"{parts[1]}-{parts[0]}"
    return v
