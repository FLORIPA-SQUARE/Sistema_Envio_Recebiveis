"""Initial schema - all 7 tables

Revision ID: 001_initial
Revises:
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable uuid-ossp extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # === usuarios ===
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("senha_hash", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === fidcs ===
    op.create_table(
        "fidcs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("nome", sa.String(50), unique=True, nullable=False),
        sa.Column("nome_completo", sa.String(300), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=True),
        sa.Column("cc_emails", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("palavras_chave", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("cor", sa.String(7), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === operacoes ===
    op.create_table(
        "operacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("numero", sa.String(50), nullable=False),
        sa.Column("fidc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fidcs.id"), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="em_processamento"),
        sa.Column("modo_envio", sa.String(20), nullable=False, server_default="preview"),
        sa.Column("total_boletos", sa.Integer(), server_default="0"),
        sa.Column("total_aprovados", sa.Integer(), server_default="0"),
        sa.Column("total_rejeitados", sa.Integer(), server_default="0"),
        sa.Column("taxa_sucesso", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_operacoes_status", "operacoes", ["status"])
    op.create_index("ix_operacoes_fidc_id", "operacoes", ["fidc_id"])

    # === xmls_nfe ===
    op.create_table(
        "xmls_nfe",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operacao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operacoes.id"), nullable=False),
        sa.Column("nome_arquivo", sa.String(500), nullable=False),
        sa.Column("numero_nota", sa.String(20), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=True),
        sa.Column("nome_destinatario", sa.String(300), nullable=True),
        sa.Column("valor_total", sa.Float(), nullable=True),
        sa.Column("emails", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("emails_invalidos", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("duplicatas", postgresql.JSONB(), server_default="[]"),
        sa.Column("xml_valido", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("dados_raw", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_xmls_nfe_operacao_id", "xmls_nfe", ["operacao_id"])
    op.create_index("ix_xmls_nfe_numero_nota", "xmls_nfe", ["numero_nota"])

    # === boletos ===
    op.create_table(
        "boletos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operacao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operacoes.id"), nullable=False),
        sa.Column("xml_nfe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("xmls_nfe.id"), nullable=True),
        sa.Column("arquivo_original", sa.String(500), nullable=False),
        sa.Column("arquivo_renomeado", sa.String(500), nullable=True),
        sa.Column("pagador", sa.String(300), nullable=True),
        sa.Column("cnpj", sa.String(20), nullable=True),
        sa.Column("numero_nota", sa.String(20), nullable=True),
        sa.Column("vencimento", sa.String(10), nullable=True),
        sa.Column("vencimento_date", sa.Date(), nullable=True),
        sa.Column("valor", sa.Float(), nullable=True),
        sa.Column("valor_formatado", sa.String(30), nullable=True),
        sa.Column("fidc_detectada", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("motivo_rejeicao", sa.String(500), nullable=True),
        sa.Column("validacao_camada1", postgresql.JSONB(), nullable=True),
        sa.Column("validacao_camada2", postgresql.JSONB(), nullable=True),
        sa.Column("validacao_camada3", postgresql.JSONB(), nullable=True),
        sa.Column("validacao_camada4", postgresql.JSONB(), nullable=True),
        sa.Column("validacao_camada5", postgresql.JSONB(), nullable=True),
        sa.Column("juros_detectado", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("arquivo_path", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_boletos_operacao_id", "boletos", ["operacao_id"])
    op.create_index("ix_boletos_status", "boletos", ["status"])
    op.create_index("ix_boletos_numero_nota", "boletos", ["numero_nota"])

    # === envios ===
    op.create_table(
        "envios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operacao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operacoes.id"), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("email_para", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("email_cc", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("assunto", sa.String(500), nullable=False),
        sa.Column("corpo_html", sa.Text(), nullable=True),
        sa.Column("modo", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("erro_detalhes", sa.Text(), nullable=True),
        sa.Column("boletos_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default="{}"),
        sa.Column("xmls_anexados", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("timestamp_envio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_envios_operacao_id", "envios", ["operacao_id"])

    # === audit_log ===
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("operacao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operacoes.id"), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("acao", sa.String(100), nullable=False),
        sa.Column("entidade", sa.String(100), nullable=True),
        sa.Column("entidade_id", sa.String(100), nullable=True),
        sa.Column("detalhes", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_operacao_id", "audit_log", ["operacao_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("envios")
    op.drop_table("boletos")
    op.drop_table("xmls_nfe")
    op.drop_table("operacoes")
    op.drop_table("fidcs")
    op.drop_table("usuarios")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
