# models/Professional.py

from datetime import date, datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Time, DateTime, text
from helpers.database import db, bcrypt

from flask_restful import fields

profissional_fields = {
    'id': fields.Integer,
    'nome': fields.String,
    'registro': fields.String,
    'especialidade': fields.String,
    'telefone': fields.String,
    'email': fields.String,
    'ativo': fields.Boolean
}

class Profissional(db.Model):
    __tablename__ = "tb_profissional"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    registro: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # CRM, CRO, Coren
    especialidade: Mapped[str] = mapped_column(String(100), nullable=False)
    telefone: Mapped[str] = mapped_column(String(15), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    ativo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))

    # Relacionamento com horarios_disponiveis (1:N)
    credencial = relationship(
        "Credencial", 
        uselist=False, 
        viewonly=True,
        primaryjoin="and_(Credencial.referencia_id == Profissional.id, Credencial.tipo == 'profissional')",
        foreign_keys="[Credencial.referencia_id]"
    )
    horarios_disponiveis = relationship("Horario", back_populates="profissional", foreign_keys="[Horario.profissional_id]")

    def __init__(self, nome: str, registro: str, especialidade: str, telefone: str, email: str, ativo: bool):
        self.nome = nome
        self.registro = registro
        self.especialidade = especialidade
        self.telefone = telefone
        self.email = email
        self.ativo = ativo

    def __repr__(self):
        return f"<profissional(nome={self.nome}, registro='{self.registro}', especialidade='{self.especialidade}', ativo='{self.ativo}')>"

    def __str__(self):
        return f"{self.nome} ({self.registro}) - {self.especialidade} - {self.ativo}"
