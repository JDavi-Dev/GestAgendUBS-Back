from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Patient(TimestampMixin, Base):
    __tablename__ = "tb_paciente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column("nome", String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column("telefone", String(11), nullable=True)
    birth_date: Mapped[date] = mapped_column("data_nascimento", Date, nullable=False)
    address: Mapped[str | None] = mapped_column("endereco", String(500), nullable=True)
    priority_group: Mapped[str] = mapped_column("grupo_prioridade", String(30), default="nenhum", nullable=False)

    appointments = relationship("Appointment", back_populates="patient", passive_deletes=True)
    waitlist_entries = relationship("WaitlistEntry", back_populates="patient", passive_deletes=True)
