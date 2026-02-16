"""Add email text fields to fidcs

Revision ID: 004_fidc_email_fields
Revises: 003_add_valores_operacao
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

revision = "004_fidc_email_fields"
down_revision = "003_add_valores_operacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fidcs", sa.Column("email_introducao", sa.String(500), nullable=True))
    op.add_column("fidcs", sa.Column("email_mensagem_fechamento", sa.String(500), nullable=True))
    op.add_column("fidcs", sa.Column("email_assinatura_nome", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("fidcs", "email_assinatura_nome")
    op.drop_column("fidcs", "email_mensagem_fechamento")
    op.drop_column("fidcs", "email_introducao")
