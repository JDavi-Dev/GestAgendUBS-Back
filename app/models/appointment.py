from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Appointment(TimestampMixin, Base):
    __tablename__ = "tb_agendamento"
    __table_args__ = (
        Index(
            "uq_active_appointment_schedule",
            "horario_id",
            unique=True,
            postgresql_where=text("status = 'scheduled'"),
            sqlite_where=text("status = 'scheduled'"),
        ),
        Index("ix_appointment_patient_status", "paciente_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        "paciente_id",
        ForeignKey("tb_paciente.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    schedule_id: Mapped[int] = mapped_column(
        "horario_id",
        ForeignKey("tb_horario.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column("motivo_cancelamento", String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column("observacoes", Text, nullable=True)

    patient = relationship("Patient", back_populates="appointments")
    schedule = relationship("Schedule", back_populates="appointments")
