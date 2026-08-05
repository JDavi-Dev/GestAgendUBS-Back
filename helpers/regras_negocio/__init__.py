from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_


def _as_date(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def _as_time(value):
    return time.fromisoformat(value) if isinstance(value, str) else value


def existe_conflito_horario(session, profissional_id, data, hora_inicio, hora_fim, ignorar_id=None):
    from models.Horario import Horario

    data = _as_date(data)
    hora_inicio = _as_time(hora_inicio)
    hora_fim = _as_time(hora_fim)

    query = session.query(Horario).filter(
        and_(
            Horario.profissional_id == profissional_id,
            Horario.data == data,
            Horario.hora_inicio < hora_fim,
            Horario.hora_fim > hora_inicio,
        )
    )
    if ignorar_id is not None:
        query = query.filter(Horario.id != ignorar_id)
    return session.query(query.exists()).scalar()


def paciente_tem_conflito(session, paciente_id, horario):
    from models.Agendamento import Agendamento
    from models.Horario import Horario

    return session.query(
        session.query(Agendamento)
        .join(Horario)
        .filter(
            Agendamento.paciente_id == paciente_id,
            Agendamento.status.in_(['agendado', 'confirmado']),
            Horario.data == horario.data,
            Horario.hora_inicio < horario.hora_fim,
            Horario.hora_fim > horario.hora_inicio,
        )
        .exists()
    ).scalar()


def cancelamento_permitido(data_consulta, hora_consulta, agora=None):
    agora = agora or datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)

    consulta = datetime.combine(_as_date(data_consulta), _as_time(hora_consulta), tzinfo=timezone.utc)
    return consulta - agora >= timedelta(hours=24)
