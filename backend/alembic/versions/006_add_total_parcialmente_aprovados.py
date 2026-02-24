"""Add total_parcialmente_aprovados to operacoes and backfill counters

Revision ID: 006_add_total_parcial
Revises: 005_add_versao_finalizacao
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

revision = "006_add_total_parcial"
down_revision = "005_add_versao_finalizacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new column
    op.add_column(
        "operacoes",
        sa.Column(
            "total_parcialmente_aprovados",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # 2. Backfill: recount from actual boleto statuses
    op.execute(
        """
        UPDATE operacoes SET
          total_parcialmente_aprovados = (
            SELECT COUNT(*) FROM boletos
            WHERE boletos.operacao_id = operacoes.id
            AND boletos.status = 'parcialmente_aprovado'
          ),
          total_aprovados = (
            SELECT COUNT(*) FROM boletos
            WHERE boletos.operacao_id = operacoes.id
            AND boletos.status = 'aprovado'
          )
        """
    )

    # 3. Recalculate taxa_sucesso
    op.execute(
        """
        UPDATE operacoes SET taxa_sucesso =
          CASE WHEN total_boletos > 0
          THEN ((total_aprovados + total_parcialmente_aprovados)::float / total_boletos * 100)
          ELSE 0 END
        """
    )


def downgrade() -> None:
    # Merge parciais back into aprovados before dropping
    op.execute(
        """
        UPDATE operacoes SET
          total_aprovados = total_aprovados + total_parcialmente_aprovados
        """
    )
    op.drop_column("operacoes", "total_parcialmente_aprovados")
