"""
OutlookMailer — automacao COM do Microsoft Outlook Desktop via pywin32.

ATENCAO: Deve rodar no HOST Windows (nunca em Docker).
Requer Outlook Desktop instalado e configurado.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.email_grouper import EmailGroup

logger = logging.getLogger(__name__)

# Constantes COM do Outlook
OL_MAIL_ITEM = 0  # olMailItem
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class OutlookMailer:
    """Servico de envio de email via COM automation do Outlook."""

    def __init__(self):
        self._outlook = None

    def _get_outlook(self):
        """Lazy init — conecta ao Outlook apenas quando necessario."""
        if self._outlook is None:
            try:
                import win32com.client
                self._outlook = win32com.client.Dispatch("Outlook.Application")
                logger.info("Conexao COM com Outlook estabelecida")
            except ImportError:
                raise RuntimeError(
                    "pywin32 nao instalado. Execute: pip install pywin32"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Nao foi possivel conectar ao Outlook. "
                    f"Verifique se o Outlook esta instalado e aberto. Erro: {e}"
                )
        return self._outlook

    def _create_mail_item(self, group: EmailGroup):
        """Cria MailItem COM com todos os campos preenchidos."""
        outlook = self._get_outlook()
        mail = outlook.CreateItem(OL_MAIL_ITEM)

        mail.To = "; ".join(group.email_para)
        if group.email_cc:
            mail.CC = "; ".join(group.email_cc)
        mail.Subject = group.assunto
        mail.HTMLBody = group.corpo_html

        # Anexar PDFs (boletos) — ja ordenados por vencimento
        for pdf_path in group.anexos_pdf:
            mail.Attachments.Add(str(pdf_path))

        # Anexar XMLs (notas fiscais)
        for xml_path in group.anexos_xml:
            mail.Attachments.Add(str(xml_path))

        return mail

    def create_draft(self, group: EmailGroup) -> bool:
        """Cria rascunho no Outlook (Modo Preview).

        O rascunho e aberto na janela do Outlook para revisao manual.
        O operador decide se envia ou descarta.

        Returns:
            True se o rascunho foi criado com sucesso.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                mail = self._create_mail_item(group)
                mail.Display(False)  # Abre rascunho sem modal
                logger.info(
                    "Rascunho criado: To=%s, Subject=%s",
                    "; ".join(group.email_para),
                    group.assunto,
                )
                return True
            except Exception as e:
                logger.warning(
                    "Tentativa %d/%d falhou ao criar rascunho: %s",
                    attempt, MAX_RETRIES, e,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                    self._outlook = None  # Reset conexao
                else:
                    logger.error("Falha ao criar rascunho apos %d tentativas", MAX_RETRIES)
                    raise RuntimeError(
                        f"Outlook nao respondeu ao criar rascunho. Erro: {e}"
                    )
        return False

    def send_email(self, group: EmailGroup) -> bool:
        """Envia email diretamente via Outlook (Modo Automatico).

        O email e enviado imediatamente sem passar pelo rascunho.

        Returns:
            True se o email foi enviado com sucesso.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                mail = self._create_mail_item(group)
                mail.Send()
                logger.info(
                    "Email enviado: To=%s, Subject=%s",
                    "; ".join(group.email_para),
                    group.assunto,
                )
                return True
            except Exception as e:
                logger.warning(
                    "Tentativa %d/%d falhou ao enviar email: %s",
                    attempt, MAX_RETRIES, e,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                    self._outlook = None  # Reset conexao
                else:
                    logger.error("Falha ao enviar email apos %d tentativas", MAX_RETRIES)
                    raise RuntimeError(
                        f"Outlook nao respondeu ao enviar email. Erro: {e}"
                    )
        return False
