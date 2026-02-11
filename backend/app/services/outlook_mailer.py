"""
OutlookMailer — automacao COM do Microsoft Outlook Desktop via pywin32.

ATENCAO: Deve rodar no HOST Windows (nunca em Docker).
Requer Outlook Desktop instalado e configurado.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.email_grouper import EmailGroup

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSINATURA_PATH = ASSETS_DIR / "assinatura.jpg"

# Constantes COM do Outlook
OL_MAIL_ITEM = 0  # olMailItem
OL_FOLDER_SENT_MAIL = 5  # olFolderSentMail
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

        # Anexar Notas Fiscais em PDF
        for xml_path in group.anexos_xml:
            mail.Attachments.Add(str(xml_path))

        # Assinatura JotaJota inline (CID embedding)
        if ASSINATURA_PATH.exists():
            att = mail.Attachments.Add(str(ASSINATURA_PATH))
            att.PropertyAccessor.SetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x3712001F",
                "assinatura_jj",
            )

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

    def verificar_itens_enviados(
        self,
        envios_pendentes: list[tuple[str, list[str]]],
    ) -> dict[str, bool]:
        """Verifica na pasta Itens Enviados do Outlook se rascunhos foram enviados.

        Args:
            envios_pendentes: Lista de (assunto, [emails_destinatarios])

        Returns:
            Dict {assunto: True/False} indicando se foi encontrado nos enviados.
        """
        resultado: dict[str, bool] = {}
        for assunto, _ in envios_pendentes:
            resultado[assunto] = False

        if not envios_pendentes:
            return resultado

        try:
            outlook = self._get_outlook()
            namespace = outlook.GetNamespace("MAPI")
            sent_folder = namespace.GetDefaultFolder(OL_FOLDER_SENT_MAIL)

            # Iterar os itens mais recentes sem filtro de data (mais confiavel cross-locale)
            itens = sent_folder.Items
            itens.Sort("[SentOn]", True)  # Mais recentes primeiro

            data_corte = datetime.now() - timedelta(hours=48)
            assuntos_enviados: list[str] = []
            count = 0

            for item in itens:
                try:
                    sent_on = item.SentOn
                    # pywin32 retorna pywintypes.datetime — converter para comparacao
                    if hasattr(sent_on, "timestamp"):
                        item_dt = datetime.fromtimestamp(sent_on.timestamp())
                    else:
                        item_dt = datetime(
                            sent_on.year, sent_on.month, sent_on.day,
                            sent_on.hour, sent_on.minute, sent_on.second,
                        )

                    if item_dt < data_corte:
                        break  # Ja passou do limite de 48h (lista ordenada desc)

                    assuntos_enviados.append(item.Subject)
                    count += 1
                    if count >= 200:  # Limite de seguranca
                        break
                except Exception:
                    continue

            logger.info(
                "Verificacao Sent Items: %d emails nas ultimas 48h", len(assuntos_enviados)
            )
            for subj in assuntos_enviados[:10]:
                logger.info("  Sent Item: %s", subj)

            # Buscar pendentes
            for assunto, _ in envios_pendentes:
                logger.info("  Procurando: '%s'", assunto)
                if assunto in assuntos_enviados:
                    resultado[assunto] = True
                    logger.info(
                        "Rascunho encontrado nos Itens Enviados: %s", assunto
                    )

        except ImportError:
            logger.warning("pywin32 nao instalado — verificacao ignorada")
        except Exception as e:
            logger.warning("Erro ao verificar Itens Enviados: %s", e)

        return resultado
