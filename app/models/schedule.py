from datetime import date, time

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Schedule(TimestampMixin, Base):
    __tablename__ = "tb_horario"
    __table_args__ = (
        CheckConstraint("hora_fim > hora_inicio", name="ck_schedule_end_after_start"),
        UniqueConstraint(
            "profissional_id",
            "data",
            "hora_inicio",
            "hora_fim",
            name="uq_schedule_exact_interval",
        ),
        Index("ix_schedule_specialty_date_status", "especialidade", "data", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    professional_id: Mapped[int] = mapped_column(
        "profissional_id",
        ForeignKey("tb_profissional.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    specialty: Mapped[str] = mapped_column("especialidade", String(100), index=True, nullable=False)
    date: Mapped[date] = mapped_column("data", Date, index=True, nullable=False)
    start_time: Mapped[time] = mapped_column("hora_inicio", Time, nullable=False)
    end_time: Mapped[time] = mapped_column("hora_fim", Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="available", index=True, nullable=False)

    professional = relationship("Professional", back_populates="schedules")
    appointments = relationship("Appointment", back_populates="schedule", passive_deletes=True)
