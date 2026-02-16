"""Add valor_bruto and valor_liquido to operacoes

Revision ID: 003_add_valores_operacao
Revises: 002_email_layouts
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

revision = "003_add_valores_operacao"
down_revision = "002_email_layouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operacoes", sa.Column("valor_bruto", sa.Float(), nullable=True))
    op.add_column("operacoes", sa.Column("valor_liquido", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("operacoes", "valor_liquido")
    op.drop_column("operacoes", "valor_bruto")
