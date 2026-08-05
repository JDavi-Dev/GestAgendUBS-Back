# models/FilaEspera.py

from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, String, Enum, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from helpers.database import db
from flask_restful import fields

fila_espera_fields = {
    'id': fields.Integer,
    'paciente_id': fields.Integer,
    'paciente_nome': fields.String,  # Campo virtual (não está no model)
    'especialidade': fields.String,
    'prioridade': fields.Integer,
    'prioridade_label': fields.String,  # Campo virtual
    'data_solicitacao': fields.String,
    'status': fields.String,
    'mensagem_status': fields.String,
    'updated_at': fields.String,
    'posicao': fields.Integer  # Campo virtual (calculado)
}

class FilaEspera(db.Model):
    __tablename__ = "tb_fila_espera"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("tb_paciente.id"), nullable=False)
    especialidade: Mapped[str] = mapped_column(String(100), nullable=False)
    prioridade: Mapped[int] = mapped_column(default=3, nullable=False)  # 1=alta, 2=média, 3=baixa
    data_solicitacao: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=text('CURRENT_TIMESTAMP'),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum('aguardando', 'alocado', 'cancelado', 'recusado', name='status_fila'), 
        default='aguardando',
        nullable=False
    )
    mensagem_status: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=text('CURRENT_TIMESTAMP'), 
        onupdate=datetime.now(timezone.utc)
    )

    # Relacionamento com Paciente
    paciente = relationship("Paciente", backref="fila_espera")

    def __init__(self, paciente_id: int, especialidade: str, prioridade: int = 3, status: str = 'aguardando', mensagem_status: str = None):
        self.paciente_id = paciente_id
        self.especialidade = especialidade
        self.prioridade = prioridade
        self.status = status
        self.mensagem_status = mensagem_status
        self.data_solicitacao = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<FilaEspera id={self.id} paciente_id={self.paciente_id} especialidade='{self.especialidade}' prioridade={self.prioridade}>"

    @staticmethod
    def calcular_prioridade(paciente) -> int:
        """
        Calcula a prioridade baseada nos critérios:
        - Prioridade 1 (Alta): idade >= 60 anos
        - Prioridade 2 (Média): gestante ou pessoa com deficiência
        - Prioridade 3 (Baixa): demais pacientes
        """
        from datetime import date
        
        # Calcular idade
        hoje = date.today()
        idade = hoje.year - paciente.data_nascimento.year - (
            (hoje.month, hoje.day) < (paciente.data_nascimento.month, paciente.data_nascimento.day)
        )
        
        if idade >= 60:
            return 1  # Alta prioridade
        if paciente.gestante or paciente.possui_deficiencia:
            return 2  # Média prioridade
        return 3  # Baixa prioridade

    @staticmethod
    def get_prioridade_label(prioridade: int) -> str:
        labels = {
            1: 'Alta',
            2: 'Média',
            3: 'Baixa'
        }
        return labels.get(prioridade, 'Desconhecida')