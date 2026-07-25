from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.dependencies import CurrentUser
from app.models import Appointment, Patient, Schedule
from app.schemas.appointment import AppointmentCreate, AppointmentStatusUpdate
from app.services.schedules import schedule_to_dict
from app.services.users import find_credential_for_profile, get_profile_by_public_id, user_to_dict

settings = get_settings()
ACTIVE_STATUS = "scheduled"


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def appointment_datetime(schedule: Schedule) -> datetime:
    return datetime.combine(schedule.date, schedule.start_time, tzinfo=ZoneInfo(settings.timezone))


def appointment_to_dict(db: Session, appointment: Appointment) -> dict:
    patient_credential = find_credential_for_profile(db, "patient", appointment.patient_id)
    professional_credential = find_credential_for_profile(
        db, "professional", appointment.schedule.professional_id
    )
    if not patient_credential or not professional_credential:
        raise HTTPException(status_code=500, detail="Credencial relacionada ao agendamento não encontrada.")

    return {
        "id": appointment.id,
        "patientId": patient_credential.id,
        "scheduleId": appointment.schedule_id,
        "status": appointment.status,
        "cancellationReason": appointment.cancellation_reason,
        "notes": appointment.notes,
        "createdAt": appointment.created_at.isoformat(),
        "schedule": schedule_to_dict(db, appointment.schedule),
        "patient": user_to_dict(db, patient_credential, include_private=True),
        "professional": user_to_dict(db, professional_credential, include_private=False),
    }


def _assert_patient_has_no_overlap(db: Session, patient_id: int, schedule: Schedule) -> None:
    conflict = db.scalar(
        select(Appointment.id)
        .join(Schedule, Schedule.id == Appointment.schedule_id)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.status == ACTIVE_STATUS,
            Schedule.date == schedule.date,
            Schedule.start_time < schedule.end_time,
            Schedule.end_time > schedule.start_time,
        )
        .limit(1)
    )
    if conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paciente já possui agendamento conflitante neste período.",
        )


def book_schedule(
    db: Session,
    *,
    patient_profile_id: int,
    schedule_id: int,
    notes: str | None = None,
) -> Appointment:
    # O bloqueio do paciente serializa agendamentos simultâneos do mesmo paciente.
    patient = db.scalar(select(Patient).where(Patient.id == patient_profile_id).with_for_update())
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    # O bloqueio do horário, somado ao índice único parcial, impede reserva dupla.
    schedule = db.scalar(select(Schedule).where(Schedule.id == schedule_id).with_for_update())
    if not schedule:
        raise HTTPException(status_code=404, detail="Horário não encontrado.")
    if schedule.status != "available":
        raise HTTPException(status_code=409, detail="Horário indisponível para agendamento.")
    if appointment_datetime(schedule) <= _local_now():
        raise HTTPException(status_code=409, detail="Não é possível agendar um horário passado.")

    _assert_patient_has_no_overlap(db, patient.id, schedule)

    appointment = Appointment(
        patient_id=patient.id,
        schedule_id=schedule.id,
        status=ACTIVE_STATUS,
        notes=notes,
    )
    schedule.status = "busy"
    db.add(appointment)
    db.flush()
    return appointment


def create_appointment(db: Session, data: AppointmentCreate, current: CurrentUser) -> dict:
    if current.role == "patient":
        patient_profile_id = current.reference_id
    elif current.role == "admin":
        if data.patient_id is None:
            raise HTTPException(status_code=422, detail="Administrador deve informar patientId.")
        _, patient = get_profile_by_public_id(db, data.patient_id, expected_role="patient")
        patient_profile_id = patient.id
    else:
        raise HTTPException(status_code=403, detail="Profissionais não podem criar agendamentos.")

    try:
        appointment = book_schedule(
            db,
            patient_profile_id=patient_profile_id,
            schedule_id=data.schedule_id,
            notes=data.notes,
        )
        db.commit()
        appointment = db.scalar(
            select(Appointment)
            .options(joinedload(Appointment.patient), joinedload(Appointment.schedule))
            .where(Appointment.id == appointment.id)
        )
        return appointment_to_dict(db, appointment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="O horário foi reservado por outro paciente. Escolha outro horário.",
        ) from exc
    except Exception:
        if db.in_transaction():
            db.rollback()
        raise


def _can_access(appointment: Appointment, current: CurrentUser) -> bool:
    if current.role == "admin":
        return True
    if current.role == "patient":
        return appointment.patient_id == current.reference_id
    if current.role == "professional":
        return appointment.schedule.professional_id == current.reference_id
    return False


def get_appointment(db: Session, appointment_id: int, current: CurrentUser) -> dict:
    appointment = db.scalar(
        select(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.schedule))
        .where(Appointment.id == appointment_id)
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    if not _can_access(appointment, current):
        raise HTTPException(status_code=403, detail="Acesso negado a este agendamento.")
    return appointment_to_dict(db, appointment)


def list_appointments(
    db: Session,
    current: CurrentUser,
    *,
    patient_public_id: int | None = None,
    professional_public_id: int | None = None,
    status_filter: str | None = None,
    date_from=None,
    date_to=None,
) -> list[dict]:
    query = (
        select(Appointment)
        .join(Schedule, Schedule.id == Appointment.schedule_id)
        .options(joinedload(Appointment.patient), joinedload(Appointment.schedule))
        .order_by(Schedule.date.desc(), Schedule.start_time.desc())
    )

    if current.role == "patient":
        query = query.where(Appointment.patient_id == current.reference_id)
    elif current.role == "professional":
        query = query.where(Schedule.professional_id == current.reference_id)
    elif current.role == "admin":
        if patient_public_id:
            _, patient = get_profile_by_public_id(db, patient_public_id, expected_role="patient")
            query = query.where(Appointment.patient_id == patient.id)
        if professional_public_id:
            _, professional = get_profile_by_public_id(
                db, professional_public_id, expected_role="professional"
            )
            query = query.where(Schedule.professional_id == professional.id)
    else:
        raise HTTPException(status_code=403, detail="Perfil sem acesso a agendamentos.")

    if status_filter:
        query = query.where(Appointment.status == status_filter)
    if date_from:
        query = query.where(Schedule.date >= date_from)
    if date_to:
        query = query.where(Schedule.date <= date_to)

    appointments = db.scalars(query).unique().all()
    return [appointment_to_dict(db, item) for item in appointments]


def cancel_appointment(
    db: Session,
    appointment_id: int,
    current: CurrentUser,
    *,
    reason: str | None = None,
    now: datetime | None = None,
) -> dict:
    appointment = db.scalar(
        select(Appointment).where(Appointment.id == appointment_id).with_for_update()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    schedule = db.scalar(
        select(Schedule).where(Schedule.id == appointment.schedule_id).with_for_update()
    )
    if not schedule:
        raise HTTPException(status_code=500, detail="Horário do agendamento não encontrado.")

    # Carrega a relação para a checagem de propriedade.
    appointment.schedule = schedule
    if current.role not in {"patient", "admin"}:
        raise HTTPException(status_code=403, detail="Apenas paciente ou administrador pode cancelar.")
    if current.role == "patient" and appointment.patient_id != current.reference_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este agendamento.")
    if appointment.status != ACTIVE_STATUS:
        raise HTTPException(status_code=409, detail="Somente agendamentos ativos podem ser cancelados.")

    local_now = now or _local_now()
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=ZoneInfo(settings.timezone))
    hours_until = (appointment_datetime(schedule) - local_now).total_seconds() / 3600
    if hours_until < 24:
        raise HTTPException(
            status_code=409,
            detail="Cancelamento permitido apenas com no mínimo 24 horas de antecedência.",
        )

    appointment.status = "cancelled"
    appointment.cancellation_reason = reason
    schedule.status = "available"
    db.commit()

    appointment = db.scalar(
        select(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.schedule))
        .where(Appointment.id == appointment.id)
    )
    return appointment_to_dict(db, appointment)


def update_appointment_status(
    db: Session,
    appointment_id: int,
    data: AppointmentStatusUpdate,
    current: CurrentUser,
) -> dict:
    appointment = db.scalar(
        select(Appointment).where(Appointment.id == appointment_id).with_for_update()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    schedule = db.get(Schedule, appointment.schedule_id)
    appointment.schedule = schedule

    if current.role == "professional" and schedule.professional_id != current.reference_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este agendamento.")
    if current.role not in {"professional", "admin"}:
        raise HTTPException(status_code=403, detail="Perfil sem permissão para registrar atendimento.")
    if appointment.status != ACTIVE_STATUS:
        raise HTTPException(status_code=409, detail="O agendamento não está ativo.")

    appointment.status = data.status
    if data.notes is not None:
        appointment.notes = data.notes
    schedule.status = "busy"
    db.commit()

    appointment = db.scalar(
        select(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.schedule))
        .where(Appointment.id == appointment.id)
    )
    return appointment_to_dict(db, appointment)
