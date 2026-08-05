"""Adiciona condições do paciente

Revision ID: a1b2c3d4e5f6
Revises: 8b7c1d2e3f4a
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '8b7c1d2e3f4a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tb_paciente',
        sa.Column('gestante', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'tb_paciente',
        sa.Column('possui_deficiencia', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column('tb_paciente', 'possui_deficiencia')
    op.drop_column('tb_paciente', 'gestante')
