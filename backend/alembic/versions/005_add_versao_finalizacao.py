"""Add versao_finalizacao to operacoes

Revision ID: 005_add_versao_finalizacao
Revises: 004_fidc_email_fields
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa

revision = "005_add_versao_finalizacao"
down_revision = "004_fidc_email_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operacoes", sa.Column("versao_finalizacao", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("operacoes", "versao_finalizacao")
