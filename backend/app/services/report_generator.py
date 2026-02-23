"""
Servico de Geracao de Relatorios — TXT (aprovados/erros) e JSON.

Formatos identicos ao sistema legado conforme PRD RF-011.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def _storage_auditoria() -> Path:
    p = Path(settings.STORAGE_DIR) / "auditoria"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _storage_erros() -> Path:
    p = Path(settings.STORAGE_DIR) / "erros"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _timestamp_str() -> str:
    return datetime.now(timezone.utc).strftime("%d%m%Y_%H%M%S")


def _format_datetime(dt) -> str:
    if dt is None:
        return "N/A"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    return str(dt)


def _camada_str(camada_dict: dict | None, num: int) -> str:
    if not camada_dict:
        return f"  Camada {num}: N/A"
    nome = camada_dict.get("nome", f"Camada {num}")
    mensagem = camada_dict.get("mensagem", "N/A")
    return f"  Camada {num} ({nome}):  {mensagem}"


def gerar_relatorio_aprovados_txt(
    operacao, boletos_aprovados, xmls_map: dict
) -> Path:
    """Gera relatorio TXT dos boletos aprovados no formato legado.

    Args:
        operacao: objeto Operacao (com .numero, .created_at)
        boletos_aprovados: lista de Boleto com status == "aprovado"
        xmls_map: dict[xml_nfe_id] -> XmlNfe record

    Returns:
        Path do arquivo gerado
    """
    ts = _timestamp_str()
    filename = f"auditoria_aprovados_{ts}.txt"
    filepath = _storage_auditoria() / filename

    total = len(boletos_aprovados)
    lines = []
    lines.append(f"RELATORIO DE AUDITORIA - BOLETOS APROVADOS")
    lines.append(f"Operacao: {operacao.numero}")
    lines.append(f"Gerado em: {_format_datetime(datetime.now(timezone.utc))}")
    lines.append(f"Total aprovados: {total}")
    lines.append("=" * 80)
    lines.append("")

    for i, boleto in enumerate(boletos_aprovados, 1):
        nome_arquivo = boleto.arquivo_renomeado or boleto.arquivo_original
        lines.append(f"[{i:03d}/{total:03d}] {nome_arquivo}")
        lines.append(f"Data/Hora: {_format_datetime(boleto.created_at)}")
        lines.append(f"Status: APROVADO")
        lines.append("")
        lines.append("VALIDACAO EM 5 CAMADAS:")
        lines.append(_camada_str(boleto.validacao_camada1, 1))
        lines.append(_camada_str(boleto.validacao_camada2, 2))
        lines.append(_camada_str(boleto.validacao_camada3, 3))
        lines.append(_camada_str(boleto.validacao_camada4, 4))
        lines.append(_camada_str(boleto.validacao_camada5, 5))
        lines.append("")

        # Dados do XML vinculado
        xml = xmls_map.get(str(boleto.xml_nfe_id)) if boleto.xml_nfe_id else None
        if xml:
            lines.append("DADOS XML:")
            lines.append(f"  Numero Nota:     {xml.numero_nota}")
            lines.append(f"  Pagador:         {xml.nome_destinatario or 'N/A'}")
            lines.append(f"  CNPJ:            {xml.cnpj or 'N/A'}")
            lines.append(f"  Valor:           R$ {xml.valor_total:,.2f}" if xml.valor_total else "  Valor:           N/A")
            emails = "; ".join(xml.emails) if xml.emails else "N/A"
            lines.append(f"  Emails:          {emails}")
        else:
            lines.append("DADOS XML: N/A")

        if boleto.juros_detectado:
            lines.append("")
            lines.append("ALERTA: Juros/multa detectado no boleto")

        lines.append("---")
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def gerar_relatorio_erros_txt(operacao, boletos_rejeitados) -> Path:
    """Gera relatorio TXT dos boletos rejeitados no formato legado.

    Args:
        operacao: objeto Operacao
        boletos_rejeitados: lista de Boleto com status == "rejeitado"

    Returns:
        Path do arquivo gerado
    """
    ts = _timestamp_str()
    filename = f"erros_{ts}.txt"
    filepath = _storage_erros() / filename

    total = len(boletos_rejeitados)
    lines = []
    lines.append(f"RELATORIO DE ERROS - BOLETOS REJEITADOS")
    lines.append(f"Operacao: {operacao.numero}")
    lines.append(f"Gerado em: {_format_datetime(datetime.now(timezone.utc))}")
    lines.append(f"Total rejeitados: {total}")
    lines.append("=" * 80)
    lines.append("")

    for i, boleto in enumerate(boletos_rejeitados, 1):
        lines.append(f"[{i:03d}/{total:03d}] {boleto.arquivo_original}")
        lines.append(f"Data/Hora: {_format_datetime(boleto.created_at)}")
        lines.append(f"Status: REJEITADO")
        lines.append("")
        lines.append("MOTIVO:")
        lines.append(f"  {boleto.motivo_rejeicao or 'Motivo nao especificado'}")
        lines.append("")
        lines.append("VALIDACAO EM 5 CAMADAS:")
        lines.append(_camada_str(boleto.validacao_camada1, 1))
        lines.append(_camada_str(boleto.validacao_camada2, 2))
        lines.append(_camada_str(boleto.validacao_camada3, 3))
        lines.append(_camada_str(boleto.validacao_camada4, 4))
        lines.append(_camada_str(boleto.validacao_camada5, 5))
        lines.append("")
        lines.append("DADOS EXTRAIDOS:")
        lines.append(f"  Pagador:         {boleto.pagador or 'N/A'}")
        lines.append(f"  Valor:           {boleto.valor_formatado or 'N/A'}")
        lines.append(f"  Vencimento:      {boleto.vencimento or 'N/A'}")
        lines.append(f"  NF:              {boleto.numero_nota or 'N/A'}")
        lines.append(f"  CNPJ:            {boleto.cnpj or 'N/A'}")
        lines.append("---")
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def gerar_relatorio_json(operacao, todos_boletos, xmls_map: dict) -> Path:
    """Gera relatorio JSON estruturado com todos os boletos.

    Args:
        operacao: objeto Operacao
        todos_boletos: lista de todos os Boleto (aprovados + rejeitados)
        xmls_map: dict[xml_nfe_id] -> XmlNfe record

    Returns:
        Path do arquivo gerado
    """
    ts = _timestamp_str()
    filename = f"auditoria_{ts}.json"
    filepath = _storage_auditoria() / filename

    agora = datetime.now(timezone.utc)
    aprovados = [b for b in todos_boletos if b.status in ("aprovado", "parcialmente_aprovado")]
    rejeitados = [b for b in todos_boletos if b.status == "rejeitado"]
    total = len(todos_boletos)

    boletos_data = []
    for i, boleto in enumerate(todos_boletos, 1):
        xml = xmls_map.get(str(boleto.xml_nfe_id)) if boleto.xml_nfe_id else None

        boleto_dict = {
            "numero_sequencial": i,
            "arquivo_original": boleto.arquivo_original,
            "arquivo_renomeado": boleto.arquivo_renomeado,
            "pagador": boleto.pagador,
            "cnpj": boleto.cnpj,
            "numero_nota": boleto.numero_nota,
            "vencimento": boleto.vencimento,
            "valor": boleto.valor,
            "valor_formatado": boleto.valor_formatado,
            "fidc_detectada": boleto.fidc_detectada,
            "status": boleto.status,
            "motivo_rejeicao": boleto.motivo_rejeicao,
            "validacao_camada1": boleto.validacao_camada1,
            "validacao_camada2": boleto.validacao_camada2,
            "validacao_camada3": boleto.validacao_camada3,
            "validacao_camada4": boleto.validacao_camada4,
            "validacao_camada5": boleto.validacao_camada5,
            "juros_detectado": boleto.juros_detectado,
        }

        if xml:
            boleto_dict["email_destinatarios"] = xml.emails or []
        else:
            boleto_dict["email_destinatarios"] = []

        boletos_data.append(boleto_dict)

    relatorio = {
        "operacao_numero": operacao.numero,
        "timestamp_geracao": agora.isoformat(),
        "resumo": {
            "total_boletos": total,
            "aprovados": len(aprovados),
            "rejeitados": len(rejeitados),
            "taxa_sucesso": round(len(aprovados) / total * 100, 2) if total > 0 else 0.0,
        },
        "boletos": boletos_data,
    }

    filepath.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return filepath
