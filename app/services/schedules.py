from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Appointment, Professional, Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.services.users import find_credential_for_profile, get_profile_by_public_id, user_to_dict


def _professional_from_public_id(db: Session, public_id: int, *, lock: bool = False):
    credential, profile = get_profile_by_public_id(db, public_id, expected_role="professional")
    if lock:
        profile = db.scalar(select(Professional).where(Professional.id == profile.id).with_for_update())
    if not credential.active or not profile.active:
        raise HTTPException(status_code=409, detail="Profissional inativo.")
    return credential, profile


def _check_overlap(
    db: Session,
    *,
    professional_id: int,
    schedule_date,
    start_time,
    end_time,
    exclude_id: int | None = None,
) -> None:
    query = select(Schedule.id).where(
        Schedule.professional_id == professional_id,
        Schedule.date == schedule_date,
        Schedule.start_time < end_time,
        Schedule.end_time > start_time,
    )
    if exclude_id is not None:
        query = query.where(Schedule.id != exclude_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe horário sobreposto para este profissional.",
        )


def schedule_to_dict(db: Session, schedule: Schedule) -> dict:
    credential = find_credential_for_profile(db, "professional", schedule.professional_id)
    if not credential:
        raise HTTPException(status_code=500, detail="Credencial do profissional não encontrada.")
    return {
        "id": schedule.id,
        "professionalId": credential.id,
        "specialty": schedule.specialty,
        "date": schedule.date,
        "startTime": schedule.start_time,
        "endTime": schedule.end_time,
        "status": schedule.status,
        "professional": user_to_dict(db, credential, include_private=False),
    }


def create_schedule(db: Session, data: ScheduleCreate) -> dict:
    credential, professional = _professional_from_public_id(db, data.professional_id, lock=True)
    _check_overlap(
        db,
        professional_id=professional.id,
        schedule_date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    schedule = Schedule(
        professional_id=professional.id,
        specialty=professional.specialty,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        status=data.status,
    )
    db.add(schedule)
    try:
        db.commit()
        db.refresh(schedule)
        return schedule_to_dict(db, schedule)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Horário duplicado ou conflitante.") from exc


def update_schedule(db: Session, schedule_id: int, data: ScheduleUpdate) -> dict:
    schedule = db.scalar(select(Schedule).where(Schedule.id == schedule_id).with_for_update())
    if not schedule:
        raise HTTPException(status_code=404, detail="Horário não encontrado.")

    active_appointment = db.scalar(
        select(Appointment.id).where(
            Appointment.schedule_id == schedule.id,
            Appointment.status == "scheduled",
        )
    )

    changes = data.model_dump(exclude_unset=True)
    if active_appointment and any(key in changes for key in {"professional_id", "date", "start_time", "end_time"}):
        raise HTTPException(status_code=409, detail="Não é possível alterar o intervalo de um horário ocupado.")

    professional = schedule.professional
    if "professional_id" in changes:
        _, professional = _professional_from_public_id(db, changes.pop("professional_id"), lock=True)

    candidate_date = changes.get("date", schedule.date)
    candidate_start = changes.get("start_time", schedule.start_time)
    candidate_end = changes.get("end_time", schedule.end_time)
    if candidate_end <= candidate_start:
        raise HTTPException(status_code=422, detail="O horário final deve ser posterior ao horário inicial.")
    if candidate_date < date.today():
        raise HTTPException(status_code=422, detail="Não é permitido definir horário em data passada.")

    _check_overlap(
        db,
        professional_id=professional.id,
        schedule_date=candidate_date,
        start_time=candidate_start,
        end_time=candidate_end,
        exclude_id=schedule.id,
    )

    requested_status = changes.get("status")
    if active_appointment and requested_status and requested_status != "busy":
        raise HTTPException(status_code=409, detail="Horário com agendamento ativo deve permanecer ocupado.")
    if not active_appointment and requested_status == "busy":
        raise HTTPException(status_code=409, detail="Horário sem agendamento não pode ser marcado como ocupado.")

    schedule.professional_id = professional.id
    schedule.specialty = professional.specialty
    schedule.date = candidate_date
    schedule.start_time = candidate_start
    schedule.end_time = candidate_end
    if requested_status:
        schedule.status = requested_status

    try:
        db.commit()
        db.refresh(schedule)
        return schedule_to_dict(db, schedule)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Horário duplicado ou conflitante.") from exc


def delete_schedule(db: Session, schedule_id: int) -> None:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Horário não encontrado.")
    linked = db.scalar(select(func.count(Appointment.id)).where(Appointment.schedule_id == schedule.id)) or 0
    if linked:
        raise HTTPException(status_code=409, detail="Não é possível excluir horário vinculado a agendamentos.")
    db.delete(schedule)
    db.commit()


def list_schedules(
    db: Session,
    *,
    specialty: str | None = None,
    schedule_date=None,
    status_filter: str | None = None,
    professional_public_id: int | None = None,
) -> list[dict]:
    query = select(Schedule).options(joinedload(Schedule.professional)).order_by(
        Schedule.date, Schedule.start_time
    )
    if specialty:
        query = query.where(func.lower(Schedule.specialty) == specialty.lower())
    if schedule_date:
        query = query.where(Schedule.date == schedule_date)
    if status_filter:
        query = query.where(Schedule.status == status_filter)
    if professional_public_id:
        _, professional = _professional_from_public_id(db, professional_public_id)
        query = query.where(Schedule.professional_id == professional.id)
    schedules = db.scalars(query).unique().all()
    return [schedule_to_dict(db, schedule) for schedule in schedules]
