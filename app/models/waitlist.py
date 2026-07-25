from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class WaitlistEntry(TimestampMixin, Base):
    __tablename__ = "tb_fila_espera"
    __table_args__ = (
        Index(
            "uq_waiting_patient_specialty",
            "paciente_id",
            "especialidade",
            unique=True,
            postgresql_where=text("status = 'aguardando'"),
            sqlite_where=text("status = 'aguardando'"),
        ),
        Index("ix_waitlist_order", "especialidade", "prioridade_ordem", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        "paciente_id",
        ForeignKey("tb_paciente.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    specialty: Mapped[str] = mapped_column("especialidade", String(100), nullable=False, index=True)
    priority: Mapped[str] = mapped_column("prioridade", String(20), nullable=False)
    priority_order: Mapped[int] = mapped_column("prioridade_ordem", Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="aguardando", nullable=False, index=True)
    allocated_schedule_id: Mapped[int | None] = mapped_column(
        "horario_alocado_id",
        ForeignKey("tb_horario.id", ondelete="SET NULL"),
        nullable=True,
    )
    allocated_appointment_id: Mapped[int | None] = mapped_column(
        "agendamento_alocado_id",
        ForeignKey("tb_agendamento.id", ondelete="SET NULL"),
        nullable=True,
    )

    patient = relationship("Patient", back_populates="waitlist_entries")
    allocated_schedule = relationship("Schedule", foreign_keys=[allocated_schedule_id])
    allocated_appointment = relationship("Appointment", foreign_keys=[allocated_appointment_id])
