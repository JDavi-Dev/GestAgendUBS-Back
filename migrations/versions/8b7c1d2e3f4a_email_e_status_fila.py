"""Adiciona email do paciente e justificativa da fila

Revision ID: 8b7c1d2e3f4a
Revises: 30ce74a5c507
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = '8b7c1d2e3f4a'
down_revision = '30ce74a5c507'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tb_paciente', sa.Column('email', sa.String(length=255), nullable=True))
    op.create_unique_constraint('tb_paciente_email_key', 'tb_paciente', ['email'])
    op.add_column('tb_fila_espera', sa.Column('mensagem_status', sa.String(length=500), nullable=True))
    op.execute("ALTER TYPE status_fila ADD VALUE IF NOT EXISTS 'recusado'")


def downgrade():
    op.drop_column('tb_fila_espera', 'mensagem_status')
    op.drop_constraint('tb_paciente_email_key', 'tb_paciente', type_='unique')
    op.drop_column('tb_paciente', 'email')
    # O PostgreSQL não remove valores de ENUM com segurança em downgrade simples.
