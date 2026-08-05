# models/Administrator.py

from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, text

from helpers.database import db, bcrypt

from flask_restful import fields

administrador_fields = {
    'id': fields.Integer,
    'nome': fields.String,
    'email': fields.String,
    'cargo': fields.String,
}

class Administrador(db.Model):
    __tablename__ = "tb_administrador"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    cargo: Mapped[str] = mapped_column(String(100), nullable=True)  # ex: "Coordenador da UBS"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))

    credencial = relationship(
        "Credencial", 
        uselist=False, 
        viewonly=True,
        primaryjoin="and_(Credencial.referencia_id == Administrador.id, Credencial.tipo == 'administrador')",
        foreign_keys="[Credencial.referencia_id]"
    )

    def __init__(self, nome: str, email: str, cargo: str):
        self.nome = nome
        self.email = email
        self.cargo = cargo

    def __repr__(self):
        return f"<administrador(nome={self.nome} - cargo='{self.cargo}'>"

    def __str__(self):
        return f"{self.nome} - {self.cargo}"