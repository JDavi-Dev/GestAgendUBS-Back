from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import CurrentUser
from app.models import Appointment, Patient, Schedule, WaitlistEntry
from app.schemas.waitlist import WaitlistAllocate, WaitlistJoin
from app.services.appointments import book_schedule
from app.services.users import find_credential_for_profile, get_profile_by_public_id, user_to_dict
from app.utils.normalization import calculate_age

PRIORITY_ORDER = {"alta": 1, "media": 2, "baixa": 3}


def calculate_priority(patient: Patient) -> tuple[str, int]:
    if calculate_age(patient.birth_date) >= 60:
        return "alta", PRIORITY_ORDER["alta"]
    if patient.priority_group in {"gestante", "pcd", "cadeirante"}:
        return "media", PRIORITY_ORDER["media"]
    return "baixa", PRIORITY_ORDER["baixa"]


def _positions(entries: list[WaitlistEntry]) -> dict[int, int]:
    positions: dict[int, int] = {}
    counters: dict[str, int] = {}
    for entry in entries:
        if entry.status != "aguardando":
            continue
        counters[entry.specialty] = counters.get(entry.specialty, 0) + 1
        positions[entry.id] = counters[entry.specialty]
    return positions


def waitlist_to_dict(db: Session, entry: WaitlistEntry, position: int | None) -> dict:
    credential = find_credential_for_profile(db, "patient", entry.patient_id)
    if not credential:
        raise HTTPException(status_code=500, detail="Credencial do paciente da fila não encontrada.")
    return {
        "id": entry.id,
        "patientId": credential.id,
        "specialty": entry.specialty,
        "priority": entry.priority,
        "status": entry.status,
        "position": position,
        "createdAt": entry.created_at.isoformat(),
        "allocatedScheduleId": entry.allocated_schedule_id,
        "allocatedAppointmentId": entry.allocated_appointment_id,
        "patient": user_to_dict(db, credential, include_private=True),
    }


def join_waitlist(db: Session, data: WaitlistJoin, current: CurrentUser) -> dict:
    if current.role == "patient":
        patient = db.get(Patient, current.reference_id)
    elif current.role == "admin":
        if data.patient_id is None:
            raise HTTPException(status_code=422, detail="Administrador deve informar patientId.")
        _, patient = get_profile_by_public_id(db, data.patient_id, expected_role="patient")
    else:
        raise HTTPException(status_code=403, detail="Perfil sem permissão para entrar na fila.")

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    available = db.scalar(
        select(Schedule.id).where(
            Schedule.specialty.ilike(data.specialty),
            Schedule.status == "available",
            Schedule.date >= date.today(),
        ).limit(1)
    )
    if available is not None:
        raise HTTPException(
            status_code=409,
            detail="Existem horários disponíveis para esta especialidade; realize o agendamento diretamente.",
        )

    existing = db.scalar(
        select(WaitlistEntry.id).where(
            WaitlistEntry.patient_id == patient.id,
            WaitlistEntry.specialty.ilike(data.specialty),
            WaitlistEntry.status == "aguardando",
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Paciente já está aguardando nesta especialidade.")

    priority, order = calculate_priority(patient)
    entry = WaitlistEntry(
        patient_id=patient.id,
        specialty=data.specialty,
        priority=priority,
        priority_order=order,
        status="aguardando",
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Paciente já está na fila desta especialidade.") from exc

    ordered = db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.specialty == entry.specialty,
            WaitlistEntry.status == "aguardando",
        ).order_by(WaitlistEntry.priority_order, WaitlistEntry.created_at, WaitlistEntry.id)
    ).all()
    position = next(index for index, item in enumerate(ordered, start=1) if item.id == entry.id)
    return waitlist_to_dict(db, entry, position)


def list_waitlist(db: Session, current: CurrentUser, specialty: str | None = None) -> list[dict]:
    if current.role not in {"patient", "admin"}:
        raise HTTPException(status_code=403, detail="Perfil sem acesso à fila de espera.")

    # As posições são calculadas sobre a fila global da especialidade, não apenas
    # sobre os itens visíveis para o paciente autenticado.
    global_query = select(WaitlistEntry).where(WaitlistEntry.status == "aguardando")
    if specialty:
        global_query = global_query.where(WaitlistEntry.specialty.ilike(specialty))
    global_entries = db.scalars(
        global_query.order_by(
            WaitlistEntry.specialty,
            WaitlistEntry.priority_order,
            WaitlistEntry.created_at,
            WaitlistEntry.id,
        )
    ).all()
    positions = _positions(global_entries)

    query = select(WaitlistEntry).options(joinedload(WaitlistEntry.patient))
    if current.role == "patient":
        query = query.where(WaitlistEntry.patient_id == current.reference_id)
    if specialty:
        query = query.where(WaitlistEntry.specialty.ilike(specialty))
    entries = db.scalars(
        query.order_by(
            WaitlistEntry.specialty,
            WaitlistEntry.priority_order,
            WaitlistEntry.created_at,
            WaitlistEntry.id,
        )
    ).unique().all()
    return [waitlist_to_dict(db, entry, positions.get(entry.id)) for entry in entries]


def cancel_waitlist_entry(db: Session, entry_id: int, current: CurrentUser) -> dict:
    entry = db.scalar(select(WaitlistEntry).where(WaitlistEntry.id == entry_id).with_for_update())
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada da fila não encontrada.")
    if current.role == "patient" and entry.patient_id != current.reference_id:
        raise HTTPException(status_code=403, detail="Acesso negado a esta entrada da fila.")
    if current.role not in {"patient", "admin"}:
        raise HTTPException(status_code=403, detail="Perfil sem permissão para cancelar entrada.")
    if entry.status != "aguardando":
        raise HTTPException(status_code=409, detail="A entrada não está aguardando.")
    entry.status = "cancelado"
    db.commit()
    return waitlist_to_dict(db, entry, None)


def allocate_waitlist_entry(
    db: Session,
    entry_id: int,
    data: WaitlistAllocate,
) -> dict:
    entry = db.scalar(select(WaitlistEntry).where(WaitlistEntry.id == entry_id).with_for_update())
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada da fila não encontrada.")
    if entry.status != "aguardando":
        raise HTTPException(status_code=409, detail="A entrada não está aguardando.")

    schedule = db.get(Schedule, data.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Horário não encontrado.")
    if schedule.specialty.lower() != entry.specialty.lower():
        raise HTTPException(status_code=409, detail="A especialidade do horário não corresponde à fila.")

    try:
        appointment = book_schedule(
            db,
            patient_profile_id=entry.patient_id,
            schedule_id=schedule.id,
            notes="Alocado pela fila de espera.",
        )
        entry.status = "alocado"
        entry.allocated_schedule_id = schedule.id
        entry.allocated_appointment_id = appointment.id
        db.commit()
        db.refresh(entry)
        return waitlist_to_dict(db, entry, None)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="O horário já foi reservado.") from exc
    except Exception:
        if db.in_transaction():
            db.rollback()
        raise
