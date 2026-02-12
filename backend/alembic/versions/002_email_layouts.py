"""Add email_layouts table

Revision ID: 002_email_layouts
Revises: 001_initial
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_email_layouts"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_layouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("nome", sa.String(100), unique=True, nullable=False),
        sa.Column("saudacao", sa.String(200), nullable=False),
        sa.Column("introducao", sa.String(200), nullable=False),
        sa.Column("mensagem_fechamento", sa.String(500), nullable=False),
        sa.Column("assinatura_nome", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("email_layouts")
