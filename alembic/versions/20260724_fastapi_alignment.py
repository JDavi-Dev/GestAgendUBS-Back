"""Alinhar esquema ao backend FastAPI e aos requisitos do TCC.

Revision ID: 20260724_fastapi
Revises: 30ce74a5c507
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_fastapi"
down_revision = "30ce74a5c507"
branch_labels = None
depends_on = None


def _postgres_upgrade() -> None:
    # Credenciais: converter enum/valores legados para perfis usados pela API.
    op.execute(
        """
        ALTER TABLE tb_credencial
        ALTER COLUMN tipo TYPE VARCHAR(30)
        USING CASE tipo::text
          WHEN 'paciente' THEN 'patient'
          WHEN 'profissional' THEN 'professional'
          WHEN 'administrador' THEN 'admin'
          ELSE tipo::text
        END
        """
    )
    op.execute("DROP TYPE IF EXISTS \"tipo_Credencial\"")
    op.create_unique_constraint(
        "uq_credential_role_reference",
        "tb_credencial",
        ["tipo", "referencia_id"],
    )
    op.create_index("ix_tb_credencial_login", "tb_credencial", ["login"], unique=False)
    op.create_index("ix_tb_credencial_tipo", "tb_credencial", ["tipo"], unique=False)
    op.execute(
        """
        UPDATE tb_credencial c
        SET ativo = p.ativo
        FROM tb_profissional p
        WHERE c.tipo = 'professional' AND c.referencia_id = p.id
        """
    )

    # Paciente.
    op.add_column("tb_paciente", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("tb_paciente", sa.Column("endereco", sa.String(length=500), nullable=True))
    op.add_column(
        "tb_paciente",
        sa.Column("grupo_prioridade", sa.String(length=30), nullable=False, server_default="nenhum"),
    )
    op.execute("UPDATE tb_paciente SET email = cpf || '@sga.local' WHERE email IS NULL")
    op.alter_column("tb_paciente", "email", nullable=False)
    op.alter_column("tb_paciente", "telefone", existing_type=sa.String(length=15), nullable=True)
    op.create_unique_constraint("uq_tb_paciente_email", "tb_paciente", ["email"])
    op.create_index("ix_tb_paciente_cpf", "tb_paciente", ["cpf"], unique=False)
    op.create_index("ix_tb_paciente_email", "tb_paciente", ["email"], unique=False)

    # Profissional.
    op.add_column("tb_profissional", sa.Column("cpf", sa.String(length=11), nullable=True))
    op.execute(
        "UPDATE tb_profissional SET email = 'professional-' || id || '@sga.local' WHERE email IS NULL"
    )
    op.alter_column("tb_profissional", "email", nullable=False)
    op.create_unique_constraint("uq_tb_profissional_cpf", "tb_profissional", ["cpf"])
    op.create_index("ix_tb_profissional_cpf", "tb_profissional", ["cpf"], unique=False)
    op.create_index("ix_tb_profissional_email", "tb_profissional", ["email"], unique=False)
    op.create_index(
        "ix_tb_profissional_especialidade",
        "tb_profissional",
        ["especialidade"],
        unique=False,
    )

    # Administrador.
    op.add_column("tb_administrador", sa.Column("cpf", sa.String(length=11), nullable=True))
    op.add_column("tb_administrador", sa.Column("telefone", sa.String(length=11), nullable=True))
    op.add_column(
        "tb_administrador",
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_unique_constraint("uq_tb_administrador_cpf", "tb_administrador", ["cpf"])
    op.create_index("ix_tb_administrador_cpf", "tb_administrador", ["cpf"], unique=False)
    op.create_index("ix_tb_administrador_email", "tb_administrador", ["email"], unique=False)

    # Horários.
    op.add_column("tb_horario", sa.Column("especialidade", sa.String(length=100), nullable=True))
    op.add_column(
        "tb_horario",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="available"),
    )
    op.execute(
        """
        UPDATE tb_horario h
        SET especialidade = p.especialidade,
            status = CASE WHEN h.disponivel THEN 'available' ELSE 'busy' END
        FROM tb_profissional p
        WHERE p.id = h.profissional_id
        """
    )
    op.alter_column("tb_horario", "especialidade", nullable=False)
    op.drop_column("tb_horario", "disponivel")
    op.create_check_constraint(
        "ck_schedule_end_after_start",
        "tb_horario",
        "hora_fim > hora_inicio",
    )
    op.create_unique_constraint(
        "uq_schedule_exact_interval",
        "tb_horario",
        ["profissional_id", "data", "hora_inicio", "hora_fim"],
    )
    op.create_index("ix_tb_horario_profissional_id", "tb_horario", ["profissional_id"])
    op.create_index("ix_tb_horario_especialidade", "tb_horario", ["especialidade"])
    op.create_index("ix_tb_horario_data", "tb_horario", ["data"])
    op.create_index("ix_tb_horario_status", "tb_horario", ["status"])
    op.create_index(
        "ix_schedule_specialty_date_status",
        "tb_horario",
        ["especialidade", "data", "status"],
    )

    # Agendamentos: normalizar status e deduplicar reservas ativas antes do índice único.
    op.add_column("tb_agendamento", sa.Column("observacoes", sa.Text(), nullable=True))
    op.execute(
        """
        WITH ranked AS (
          SELECT id,
                 ROW_NUMBER() OVER (PARTITION BY horario_id ORDER BY id) AS rn
          FROM tb_agendamento
          WHERE status IN ('agendado', 'confirmado', 'scheduled')
        )
        UPDATE tb_agendamento
        SET status = 'cancelled',
            motivo_cancelamento = COALESCE(motivo_cancelamento, 'Duplicidade corrigida na migração')
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.execute(
        """
        UPDATE tb_agendamento
        SET status = CASE status
          WHEN 'agendado' THEN 'scheduled'
          WHEN 'confirmado' THEN 'scheduled'
          WHEN 'cancelado' THEN 'cancelled'
          WHEN 'realizado' THEN 'done'
          WHEN 'falta' THEN 'missed'
          ELSE status
        END
        """
    )
    op.drop_column("tb_agendamento", "data_agendamento")
    op.create_index("ix_tb_agendamento_paciente_id", "tb_agendamento", ["paciente_id"])
    op.create_index("ix_tb_agendamento_horario_id", "tb_agendamento", ["horario_id"])
    op.create_index("ix_tb_agendamento_status", "tb_agendamento", ["status"])
    op.create_index(
        "ix_appointment_patient_status",
        "tb_agendamento",
        ["paciente_id", "status"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_active_appointment_schedule "
        "ON tb_agendamento (horario_id) WHERE status = 'scheduled'"
    )

    # Fila de espera.
    op.execute("ALTER TABLE tb_fila_espera RENAME COLUMN prioridade TO prioridade_ordem")
    op.add_column("tb_fila_espera", sa.Column("prioridade", sa.String(length=20), nullable=True))
    op.add_column("tb_fila_espera", sa.Column("horario_alocado_id", sa.Integer(), nullable=True))
    op.add_column("tb_fila_espera", sa.Column("agendamento_alocado_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE tb_fila_espera
        SET prioridade = CASE prioridade_ordem
          WHEN 1 THEN 'alta'
          WHEN 2 THEN 'media'
          ELSE 'baixa'
        END,
        created_at = COALESCE(data_solicitacao, created_at)
        """
    )
    op.alter_column("tb_fila_espera", "prioridade", nullable=False)
    op.create_foreign_key(
        "fk_waitlist_allocated_schedule",
        "tb_fila_espera",
        "tb_horario",
        ["horario_alocado_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_waitlist_allocated_appointment",
        "tb_fila_espera",
        "tb_agendamento",
        ["agendamento_alocado_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        WITH ranked AS (
          SELECT id,
                 ROW_NUMBER() OVER (
                   PARTITION BY paciente_id, LOWER(especialidade)
                   ORDER BY created_at, id
                 ) AS rn
          FROM tb_fila_espera
          WHERE status = 'aguardando'
        )
        UPDATE tb_fila_espera
        SET status = 'cancelado'
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.create_index("ix_tb_fila_espera_paciente_id", "tb_fila_espera", ["paciente_id"])
    op.create_index("ix_tb_fila_espera_especialidade", "tb_fila_espera", ["especialidade"])
    op.create_index("ix_tb_fila_espera_status", "tb_fila_espera", ["status"])
    op.create_index(
        "ix_waitlist_order",
        "tb_fila_espera",
        ["especialidade", "prioridade_ordem", "created_at"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_waiting_patient_specialty "
        "ON tb_fila_espera (paciente_id, especialidade) WHERE status = 'aguardando'"
    )

    op.create_table(
        "tb_token_revogado",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_tb_token_revogado_expires_at", "tb_token_revogado", ["expires_at"])


def _sqlite_upgrade() -> None:
    # Caminho destinado apenas a bancos legados de desenvolvimento em SQLite.
    # Batch mode recria tabelas quando necessário.
    with op.batch_alter_table("tb_credencial") as batch:
        batch.alter_column("tipo", existing_type=sa.String(), type_=sa.String(length=30))
        batch.create_unique_constraint(
            "uq_credential_role_reference", ["tipo", "referencia_id"]
        )
        batch.create_index("ix_tb_credencial_login", ["login"])
        batch.create_index("ix_tb_credencial_tipo", ["tipo"])
    op.execute(
        "UPDATE tb_credencial SET tipo = CASE tipo "
        "WHEN 'paciente' THEN 'patient' WHEN 'profissional' THEN 'professional' "
        "WHEN 'administrador' THEN 'admin' ELSE tipo END"
    )
    op.execute(
        "UPDATE tb_credencial SET ativo = "
        "COALESCE((SELECT ativo FROM tb_profissional p WHERE p.id = tb_credencial.referencia_id), ativo) "
        "WHERE tipo = 'professional'"
    )

    with op.batch_alter_table("tb_paciente") as batch:
        batch.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("endereco", sa.String(length=500), nullable=True))
        batch.add_column(
            sa.Column("grupo_prioridade", sa.String(length=30), nullable=False, server_default="nenhum")
        )
    op.execute("UPDATE tb_paciente SET email = cpf || '@sga.local' WHERE email IS NULL")
    with op.batch_alter_table("tb_paciente") as batch:
        batch.alter_column("email", nullable=False)
        batch.alter_column("telefone", existing_type=sa.String(length=15), nullable=True)
        batch.create_unique_constraint("uq_tb_paciente_email", ["email"])
        batch.create_index("ix_tb_paciente_cpf", ["cpf"])
        batch.create_index("ix_tb_paciente_email", ["email"])

    with op.batch_alter_table("tb_profissional") as batch:
        batch.add_column(sa.Column("cpf", sa.String(length=11), nullable=True))
    op.execute(
        "UPDATE tb_profissional SET email = 'professional-' || id || '@sga.local' WHERE email IS NULL"
    )
    with op.batch_alter_table("tb_profissional") as batch:
        batch.alter_column("email", nullable=False)
        batch.create_unique_constraint("uq_tb_profissional_cpf", ["cpf"])
        batch.create_index("ix_tb_profissional_cpf", ["cpf"])
        batch.create_index("ix_tb_profissional_email", ["email"])
        batch.create_index("ix_tb_profissional_especialidade", ["especialidade"])

    with op.batch_alter_table("tb_administrador") as batch:
        batch.add_column(sa.Column("cpf", sa.String(length=11), nullable=True))
        batch.add_column(sa.Column("telefone", sa.String(length=11), nullable=True))
        batch.add_column(sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_unique_constraint("uq_tb_administrador_cpf", ["cpf"])
        batch.create_index("ix_tb_administrador_cpf", ["cpf"])
        batch.create_index("ix_tb_administrador_email", ["email"])

    with op.batch_alter_table("tb_horario") as batch:
        batch.add_column(sa.Column("especialidade", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="available"))
    op.execute(
        "UPDATE tb_horario SET especialidade = "
        "(SELECT especialidade FROM tb_profissional WHERE id = tb_horario.profissional_id), "
        "status = CASE WHEN disponivel = 1 THEN 'available' ELSE 'busy' END"
    )
    with op.batch_alter_table("tb_horario") as batch:
        batch.alter_column("especialidade", nullable=False)
        batch.drop_column("disponivel")
        batch.create_check_constraint("ck_schedule_end_after_start", "hora_fim > hora_inicio")
        batch.create_unique_constraint(
            "uq_schedule_exact_interval", ["profissional_id", "data", "hora_inicio", "hora_fim"]
        )
        batch.create_index("ix_tb_horario_profissional_id", ["profissional_id"])
        batch.create_index("ix_tb_horario_especialidade", ["especialidade"])
        batch.create_index("ix_tb_horario_data", ["data"])
        batch.create_index("ix_tb_horario_status", ["status"])
        batch.create_index("ix_schedule_specialty_date_status", ["especialidade", "data", "status"])

    with op.batch_alter_table("tb_agendamento") as batch:
        batch.add_column(sa.Column("observacoes", sa.Text(), nullable=True))
        batch.drop_column("data_agendamento")
        batch.create_index("ix_tb_agendamento_paciente_id", ["paciente_id"])
        batch.create_index("ix_tb_agendamento_horario_id", ["horario_id"])
        batch.create_index("ix_tb_agendamento_status", ["status"])
        batch.create_index("ix_appointment_patient_status", ["paciente_id", "status"])
    op.execute(
        "UPDATE tb_agendamento SET status = CASE status "
        "WHEN 'agendado' THEN 'scheduled' WHEN 'confirmado' THEN 'scheduled' "
        "WHEN 'cancelado' THEN 'cancelled' WHEN 'realizado' THEN 'done' "
        "WHEN 'falta' THEN 'missed' ELSE status END"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_active_appointment_schedule "
        "ON tb_agendamento (horario_id) WHERE status = 'scheduled'"
    )

    with op.batch_alter_table("tb_fila_espera") as batch:
        batch.alter_column("prioridade", new_column_name="prioridade_ordem")
    with op.batch_alter_table("tb_fila_espera") as batch:
        batch.add_column(sa.Column("prioridade", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("horario_alocado_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("agendamento_alocado_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE tb_fila_espera SET prioridade = CASE prioridade_ordem "
        "WHEN 1 THEN 'alta' WHEN 2 THEN 'media' ELSE 'baixa' END"
    )
    with op.batch_alter_table("tb_fila_espera") as batch:
        batch.alter_column("prioridade", nullable=False)
        batch.create_foreign_key(
            "fk_waitlist_allocated_schedule", "tb_horario", ["horario_alocado_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_foreign_key(
            "fk_waitlist_allocated_appointment", "tb_agendamento", ["agendamento_alocado_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_tb_fila_espera_paciente_id", ["paciente_id"])
        batch.create_index("ix_tb_fila_espera_especialidade", ["especialidade"])
        batch.create_index("ix_tb_fila_espera_status", ["status"])
        batch.create_index("ix_waitlist_order", ["especialidade", "prioridade_ordem", "created_at"])
    op.execute(
        "CREATE UNIQUE INDEX uq_waiting_patient_specialty "
        "ON tb_fila_espera (paciente_id, especialidade) WHERE status = 'aguardando'"
    )

    op.create_table(
        "tb_token_revogado",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_tb_token_revogado_expires_at", "tb_token_revogado", ["expires_at"])


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        _postgres_upgrade()
    elif dialect == "sqlite":
        _sqlite_upgrade()
    else:
        raise RuntimeError(f"Dialeto não suportado pela migração: {dialect}")


def downgrade() -> None:
    # Downgrade destrutivo não é oferecido para preservar dados migrados.
    raise RuntimeError("Downgrade não suportado para a migração de alinhamento FastAPI.")
