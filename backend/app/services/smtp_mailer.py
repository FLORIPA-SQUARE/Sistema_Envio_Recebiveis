"""
SMTPMailer — envio de emails via SMTP usando bibliotecas nativas do Python.

Substitui o OutlookMailer (COM automation). Nao requer Outlook Desktop.
Configuracao via variaveis SMTP_* no .env.
"""

from __future__ import annotations

import logging
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.email_grouper import EmailGroup

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSINATURA_PATH = ASSETS_DIR / "assinatura.jpg"

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class SMTPMailer:
    """Envio de emails via SMTP com suporte a anexos, CID inline e BCC automatico."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        use_tls: bool,
        from_email: str,
        from_name: str,
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._use_tls = use_tls
        self._from_email = from_email
        self._from_name = from_name

    def _build_message(self, group: EmailGroup) -> MIMEMultipart:
        """Constroi mensagem MIME com HTML, assinatura inline e anexos PDF."""
        # Container principal (mixed = texto + anexos)
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = "; ".join(group.email_para)
        if group.email_cc:
            msg["Cc"] = "; ".join(group.email_cc)
        msg["Subject"] = group.assunto
        # BCC NAO vai no header — invisivel pro destinatario

        # Sub-container "related" (HTML + imagem CID inline)
        related = MIMEMultipart("related")
        html_part = MIMEText(group.corpo_html, "html", "utf-8")
        related.attach(html_part)

        # Assinatura inline via CID
        if ASSINATURA_PATH.exists():
            with open(ASSINATURA_PATH, "rb") as f:
                img = MIMEImage(f.read(), _subtype="jpeg")
            img.add_header("Content-ID", "<assinatura_jj>")
            img.add_header("Content-Disposition", "inline", filename="assinatura.jpg")
            related.attach(img)

        msg.attach(related)

        # Anexos: boletos PDF
        for pdf_path in group.anexos_pdf:
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    att = MIMEApplication(f.read(), _subtype="pdf")
                att.add_header(
                    "Content-Disposition", "attachment", filename=pdf_path.name
                )
                msg.attach(att)

        # Anexos: NF PDFs
        for xml_path in group.anexos_xml:
            if xml_path.exists():
                with open(xml_path, "rb") as f:
                    att = MIMEApplication(f.read(), _subtype="pdf")
                att.add_header(
                    "Content-Disposition", "attachment", filename=xml_path.name
                )
                msg.attach(att)

        return msg

    def _send_smtp(self, msg: MIMEMultipart, recipients: list[str]) -> None:
        """Conecta ao servidor SMTP e envia a mensagem."""
        server = smtplib.SMTP(self._host, self._port, timeout=30)
        try:
            server.ehlo()
            if self._use_tls:
                server.starttls()
                server.ehlo()
            if self._user and self._password:
                server.login(self._user, self._password)
            server.sendmail(self._from_email, recipients, msg.as_string())
        finally:
            try:
                server.quit()
            except smtplib.SMTPServerDisconnected:
                pass

    def create_draft(self, group: EmailGroup) -> bool:
        """Cria 'rascunho' — no SMTP, o rascunho fica no banco (Envio record).

        Este metodo e um no-op intencional. O usuario revisa o email
        no browser e confirma o envio via endpoint /confirmar.
        """
        logger.info(
            "Rascunho SMTP (salvo no banco): Para=%s, Assunto=%s",
            "; ".join(group.email_para),
            group.assunto,
        )
        return True

    def send_email(self, group: EmailGroup) -> bool:
        """Envia email via SMTP com retry e BCC automatico para o remetente."""
        # Destinatarios reais: To + Cc + BCC (remetente)
        all_recipients = list(group.email_para) + list(group.email_cc)
        if self._from_email and self._from_email not in all_recipients:
            all_recipients.append(self._from_email)  # BCC silencioso

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                msg = self._build_message(group)
                self._send_smtp(msg, all_recipients)
                logger.info(
                    "Email SMTP enviado: Para=%s, Assunto=%s",
                    "; ".join(group.email_para),
                    group.assunto,
                )
                return True
            except Exception as e:
                logger.warning(
                    "SMTP tentativa %d/%d falhou: %s", attempt, MAX_RETRIES, e
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                else:
                    raise RuntimeError(
                        f"SMTP falhou apos {MAX_RETRIES} tentativas: {e}"
                    ) from e
        return False
