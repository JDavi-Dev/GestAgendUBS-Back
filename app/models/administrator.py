from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Administrator(TimestampMixin, Base):
    __tablename__ = "tb_administrador"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column("nome", String(255), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column("telefone", String(11), nullable=True)
    position: Mapped[str | None] = mapped_column("cargo", String(100), nullable=True)
    active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
