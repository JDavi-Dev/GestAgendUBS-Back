# CPF, nome, telefone, data de nascimento

from datetime import date, datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Date, DateTime, text

from helpers.database import db, bcrypt

from flask_restful import fields

paciente_fields = {
    'id': fields.Integer,
    'cpf': fields.String,
    'nome': fields.String,
    'email': fields.String,
    'telefone': fields.String,
    'data_nascimento': fields.String
}

class Paciente(db.Model):
    __tablename__ = "tb_paciente"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    telefone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))

    credencial = relationship(
        "Credencial", 
        uselist=False, 
        viewonly=True,
        primaryjoin="and_(Credencial.referencia_id == Paciente.id, Credencial.tipo == 'paciente')",
        foreign_keys="[Credencial.referencia_id]"
    )
    agendamentos = relationship("Agendamento", back_populates="paciente")

    def __init__(self, cpf: str, nome: str, email: str, telefone: str, data_nascimento: date):
        self.cpf = cpf
        self.nome = nome
        self.email = email
        self.telefone = telefone
        self.data_nascimento = data_nascimento

    def __repr__(self):
        return f"<paciente(nome='{self.nome}', telefone='{self.telefone}', data_nascimento='{self.data_nascimento}')>"

    def __str__(self):
        return f"{self.nome} ({self.telefone}) - {self.data_nascimento}"