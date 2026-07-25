from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUserDep
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
)
from app.services import appointments as appointment_service

router = APIRouter(prefix="/appointments", tags=["Agendamentos"])


@router.get("", response_model=list[AppointmentResponse], summary="Consultar agendamentos e histórico")
def list_appointments(
    current: CurrentUserDep,
    patient_id: int | None = Query(default=None, alias="patientId"),
    professional_id: int | None = Query(default=None, alias="professionalId"),
    status_filter: Literal["scheduled", "cancelled", "done", "missed"] | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    db: Session = Depends(get_db),
):
    return appointment_service.list_appointments(
        db,
        current,
        patient_public_id=patient_id,
        professional_public_id=professional_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED, summary="Agendar consulta")
def create_appointment(
    payload: AppointmentCreate,
    current: CurrentUserDep,
    db: Session = Depends(get_db),
):
    return appointment_service.create_appointment(db, payload, current)


@router.get("/{appointment_id}", response_model=AppointmentResponse, summary="Consultar agendamento")
def get_appointment(appointment_id: int, current: CurrentUserDep, db: Session = Depends(get_db)):
    return appointment_service.get_appointment(db, appointment_id, current)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse, summary="Cancelar agendamento")
def cancel_appointment(
    appointment_id: int,
    current: CurrentUserDep,
    db: Session = Depends(get_db),
    payload: AppointmentCancel | None = None,
):
    return appointment_service.cancel_appointment(
        db,
        appointment_id,
        current,
        reason=payload.reason if payload else None,
    )


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse, summary="Registrar atendimento ou falta")
def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    current: CurrentUserDep,
    db: Session = Depends(get_db),
):
    return appointment_service.update_appointment_status(db, appointment_id, payload, current)
