# models/horario.py

from datetime import date, time, datetime, timezone

from sqlalchemy import Date, Time, DateTime, Boolean, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from helpers.database import db

from flask_restful import fields

horario_fields = {
    'id': fields.Integer,
    'profissional_id': fields.Integer,
    'data': fields.String,
    'hora_inicio': fields.String,
    'hora_fim': fields.String,
    'disponivel': fields.Boolean,
}

class Horario(db.Model):
    __tablename__ = "tb_horario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profissional_id: Mapped[int] = mapped_column(ForeignKey("tb_profissional.id"), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fim: Mapped[time] = mapped_column(Time, nullable=False)
    disponivel: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))

    profissional = relationship("Profissional", back_populates="horarios_disponiveis")
    agendamentos = relationship("Agendamento", back_populates="horario")

    def __init__(self, profissional_id: int, data: date, hora_inicio: time, hora_fim: time, disponivel: bool):
        self.profissional_id = profissional_id
        self.data = data
        self.hora_inicio = hora_inicio
        self.hora_fim = hora_fim
        self.disponivel = disponivel

    def __repr__(self):
        return f"<horario(profissional_id={self.profissional_id}, data='{self.data}', hora_inicio='{self.hora_inicio}', hora_fim='{self.hora_fim} disponivel={self.disponivel}')>"

    def __str__(self):
        return f"{self.data} ({self.hora_inicio}) - {self.hora_fim}"