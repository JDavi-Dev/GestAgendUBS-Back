# models/agendamento.py

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from helpers.database import db

from flask_restful import fields

agendamento_fields = {
    'id': fields.Integer,
    'paciente_id': fields.Integer,
    'horario_id': fields.Integer,
    'data_agendamento': fields.String,
    'status': fields.String,
    'motivo_cancelamento': fields.String,
}

class Agendamento(db.Model):
    __tablename__ = "tb_agendamento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("tb_paciente.id"), nullable=False)
    horario_id: Mapped[int] = mapped_column(ForeignKey("tb_horario.id"), nullable=False)
    data_agendamento: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="agendado", nullable=False)  # agendado, confirmado, cancelado, realizado, falta
    motivo_cancelamento: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.now(timezone.utc))

    paciente = relationship("Paciente", back_populates="agendamentos")
    horario = relationship("Horario", back_populates="agendamentos")

    def __init__(self, paciente_id: int, horario_id: int, status: str = "agendado", motivo_cancelamento: str = None):
        self.paciente_id = paciente_id
        self.horario_id = horario_id
        self.data_agendamento = datetime.now(timezone.utc)
        self.status = status
        self.motivo_cancelamento = motivo_cancelamento

    def __repr__(self):
        return f"<agendamento(paciente_id={self.paciente_id}, horario_id={self.horario_id}'), data_agendamento='{self.data_agendamento}', status='{self.status}', motivo_cancelamento='{self.motivo_cancelamento}>"

    def __str__(self):
        return f"{self.data_agendamento} ({self.status}) - {self.motivo_cancelamento}"