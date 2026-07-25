from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminDep, CurrentUserDep
from app.schemas.waitlist import WaitlistAllocate, WaitlistJoin, WaitlistResponse
from app.services import waitlist as waitlist_service

router = APIRouter(prefix="/waitlist", tags=["Fila de Espera"])


@router.get("", response_model=list[WaitlistResponse], summary="Consultar fila de espera")
def list_waitlist(
    current: CurrentUserDep,
    specialty: str | None = None,
    db: Session = Depends(get_db),
):
    return waitlist_service.list_waitlist(db, current, specialty=specialty)


@router.post("", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED, summary="Entrar na fila de espera")
def join_waitlist(payload: WaitlistJoin, current: CurrentUserDep, db: Session = Depends(get_db)):
    return waitlist_service.join_waitlist(db, payload, current)


@router.patch("/{entry_id}/cancel", response_model=WaitlistResponse, summary="Cancelar entrada na fila")
def cancel_entry(
    entry_id: int,
    current: CurrentUserDep,
    db: Session = Depends(get_db),
):
    return waitlist_service.cancel_waitlist_entry(db, entry_id, current)


@router.post("/{entry_id}/allocate", response_model=WaitlistResponse, summary="Alocar paciente da fila em horário")
def allocate_entry(
    entry_id: int,
    payload: WaitlistAllocate,
    _: AdminDep,
    db: Session = Depends(get_db),
):
    return waitlist_service.allocate_waitlist_entry(db, entry_id, payload)
