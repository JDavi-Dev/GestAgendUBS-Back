# models/Credencial.py

from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Enum, text, Integer
from helpers.database import db, bcrypt
from flask_restful import fields

credencial_fields = {
    'id': fields.Integer,
    'login': fields.String,
    'tipo': fields.String,
    'referencia_id': fields.Integer,
    'ativo': fields.Boolean
}

class Credencial(db.Model):
    __tablename__ = "tb_credencial"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(Enum('paciente', 'profissional', 'administrador', name='tipo_Credencial'), nullable=False)
    referencia_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ativo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))
    
    def __init__(self, login: str, senha: str, tipo: str, referencia_id: int):
        self.login = login
        self.senha = bcrypt.generate_password_hash(senha).decode('utf-8')
        self.tipo = tipo
        self.referencia_id = referencia_id
    
    def __repr__(self):
        return f"<Credencial(tipo='{self.tipo}, referencia_id={self.referencia_id}'>"

    def __str__(self):
        return f"{self.tipo} - {self.referencia_id}"

    def verificar_senha(self, senha_plana: str) -> bool:
        return bcrypt.check_password_hash(self.senha, senha_plana)