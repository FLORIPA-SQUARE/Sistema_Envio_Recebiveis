"""
Servico de Audit Logging — registra acoes no banco para rastreabilidade.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def registrar_audit(
    db: AsyncSession,
    acao: str,
    operacao_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    entidade: str | None = None,
    entidade_id: str | None = None,
    detalhes: dict | None = None,
) -> None:
    """Registra uma entrada no audit_log."""
    log = AuditLog(
        operacao_id=operacao_id,
        usuario_id=usuario_id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
    )
    db.add(log)
