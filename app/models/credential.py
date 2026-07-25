from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Credential(TimestampMixin, Base):
    __tablename__ = "tb_credencial"
    __table_args__ = (UniqueConstraint("tipo", "referencia_id", name="uq_credential_role_reference"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("senha", String(255), nullable=False)
    role: Mapped[str] = mapped_column("tipo", String(30), index=True, nullable=False)
    reference_id: Mapped[int] = mapped_column("referencia_id", Integer, nullable=False)
    active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)


class RevokedToken(Base):
    __tablename__ = "tb_token_revogado"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
