from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminDep, CurrentUserDep
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services import schedules as schedule_service

router = APIRouter(prefix="/schedules", tags=["Horários"])


@router.get("", response_model=list[ScheduleResponse], summary="Consultar horários disponíveis")
def list_schedules(
    _: CurrentUserDep,
    specialty: str | None = None,
    schedule_date: date | None = Query(default=None, alias="date"),
    status_filter: Literal["available", "busy", "blocked"] | None = Query(default=None, alias="status"),
    professional_id: int | None = Query(default=None, alias="professionalId"),
    db: Session = Depends(get_db),
):
    return schedule_service.list_schedules(
        db,
        specialty=specialty,
        schedule_date=schedule_date,
        status_filter=status_filter,
        professional_public_id=professional_id,
    )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar horário")
def create_schedule(payload: ScheduleCreate, _: AdminDep, db: Session = Depends(get_db)):
    return schedule_service.create_schedule(db, payload)


@router.put("/{schedule_id}", response_model=ScheduleResponse, summary="Atualizar horário")
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    _: AdminDep,
    db: Session = Depends(get_db),
):
    return schedule_service.update_schedule(db, schedule_id, payload)


@router.delete("/{schedule_id}", status_code=204, summary="Excluir horário")
def delete_schedule(schedule_id: int, _: AdminDep, db: Session = Depends(get_db)):
    schedule_service.delete_schedule(db, schedule_id)
    return None
