from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Professional(TimestampMixin, Base):
    __tablename__ = "tb_profissional"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column("nome", String(255), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column("telefone", String(11), nullable=True)
    specialty: Mapped[str] = mapped_column("especialidade", String(100), index=True, nullable=False)
    council: Mapped[str] = mapped_column("registro", String(80), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)

    schedules = relationship("Schedule", back_populates="professional", passive_deletes=True)
