from datetime import date, datetime, time, timezone

from helpers.regras_negocio import (
    cancelamento_permitido,
    existe_conflito_horario,
    paciente_tem_conflito,
)
from models.Agendamento import Agendamento
from models.Horario import Horario
from models.Paciente import Paciente
from models.Profissional import Profissional


def criar_profissional(session, registro):
    profissional = Profissional(
        nome='Profissional Teste',
        registro=registro,
        especialidade='Clínica Geral',
        telefone='85999999999',
        email=f'{registro.lower()}@teste.com',
        ativo=True,
    )
    session.add(profissional)
    session.flush()
    return profissional


def test_impede_duplo_agendamento_no_mesmo_horario(banco_limpo):
    paciente = Paciente(
        cpf='11122233300',
        nome='Paciente Teste',
        email='paciente@teste.com',
        telefone='85988887777',
        data_nascimento=date(1990, 1, 1),
    )
    profissional_a = criar_profissional(banco_limpo, 'CRM-1')
    profissional_b = criar_profissional(banco_limpo, 'CRM-2')
    banco_limpo.add(paciente)
    banco_limpo.flush()

    horario_ocupado = Horario(profissional_a.id, date(2026, 8, 10), time(9), time(10), False)
    horario_mesmo_momento = Horario(profissional_b.id, date(2026, 8, 10), time(9, 30), time(10, 30), True)
    horario_diferente = Horario(profissional_b.id, date(2026, 8, 10), time(10), time(11), True)
    banco_limpo.add_all([horario_ocupado, horario_mesmo_momento, horario_diferente])
    banco_limpo.flush()
    banco_limpo.add(Agendamento(paciente.id, horario_ocupado.id))
    banco_limpo.commit()

    assert paciente_tem_conflito(banco_limpo, paciente.id, horario_mesmo_momento) is True
    assert paciente_tem_conflito(banco_limpo, paciente.id, horario_diferente) is False


def test_cancelamento_exige_24_horas_de_antecedencia():
    agora = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)

    assert cancelamento_permitido(date(2026, 8, 5), time(12, 0), agora) is True
    assert cancelamento_permitido(date(2026, 8, 5), time(11, 59), agora) is False


def test_detecta_conflito_de_horarios_do_profissional(banco_limpo):
    profissional = criar_profissional(banco_limpo, 'CRM-3')
    banco_limpo.add(Horario(profissional.id, date(2026, 8, 12), time(9), time(10), True))
    banco_limpo.commit()

    assert existe_conflito_horario(
        banco_limpo, profissional.id, date(2026, 8, 12), time(9, 30), time(10, 30)
    ) is True
    assert existe_conflito_horario(
        banco_limpo, profissional.id, date(2026, 8, 12), time(10), time(11)
    ) is False
