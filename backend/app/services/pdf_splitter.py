"""
Serviço de split automático de PDFs multipage.

Substitui iLovePDF (risco LGPD) por PyPDF2 local.
RNF-002: Split de 50 páginas < 10s.
"""

from pathlib import Path

from PyPDF2 import PdfReader, PdfWriter


def split_pdf(input_path: Path, output_dir: Path) -> list[Path]:
    """Divide um PDF multipágina em PDFs individuais de 1 página.

    Se o PDF tem apenas 1 página, copia o arquivo como está.

    Args:
        input_path: Caminho do PDF original.
        output_dir: Diretório para salvar os PDFs individuais.

    Returns:
        Lista de caminhos dos PDFs individuais criados.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)
    stem = input_path.stem

    if total_pages == 1:
        # PDF de 1 página: copia direto
        out_path = output_dir / input_path.name
        if out_path != input_path:
            out_path.write_bytes(input_path.read_bytes())
        return [out_path]

    # PDF multipágina: split em individuais
    output_files: list[Path] = []
    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)

        out_name = f"{stem}_p{i:03d}.pdf"
        out_path = output_dir / out_name
        with open(out_path, "wb") as f:
            writer.write(f)

        output_files.append(out_path)

    return output_files


def get_page_count(file_path: Path) -> int:
    """Retorna o número de páginas de um PDF."""
    reader = PdfReader(str(file_path))
    return len(reader.pages)
