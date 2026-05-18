# models/Administrator.py

from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column
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
    senha: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str] = mapped_column(String(100), nullable=True)  # ex: "Coordenador da UBS"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))

    def __init__(self, nome: str, email: str, senha: str, cargo: str):
        self.nome = nome
        self.email = email
        self.senha = bcrypt.generate_password_hash(senha).decode('utf-8')
        self.cargo = cargo

    def __repr__(self):
        return f"<administrador(nome={self.nome} - cargo='{self.cargo}'>"

    def __str__(self):
        return f"{self.nome} - {self.cargo}"
    
    def verificar_senha(self, senha_texto_plano):
        return bcrypt.check_password_hash(self.senha, senha_texto_plano)