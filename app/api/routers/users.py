from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminDep, CurrentUserDep
from app.schemas.user import PatientRegister, UserCreate, UserResponse, UserUpdate
from app.services import users as user_service

router = APIRouter(tags=["Usuários"])


@router.post(
    "/patients/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar paciente",
)
def register_patient(payload: PatientRegister, db: Session = Depends(get_db)):
    return user_service.register_patient(db, payload)


@router.get("/users", response_model=list[UserResponse], summary="Consultar usuários")
def list_users(
    current: CurrentUserDep,
    role: Literal["patient", "professional", "admin"] = Query(...),
    db: Session = Depends(get_db),
):
    if current.role != "admin" and role != "professional":
        raise HTTPException(status_code=403, detail="Apenas administradores podem consultar este perfil.")
    return user_service.list_users(db, role, include_private=current.role == "admin")


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário por perfil",
)
def create_user(payload: UserCreate, _: AdminDep, db: Session = Depends(get_db)):
    return user_service.create_user(db, payload)


@router.get("/users/{credential_id}", response_model=UserResponse, summary="Consultar usuário")
def get_user(credential_id: int, current: CurrentUserDep, db: Session = Depends(get_db)):
    if current.role != "admin" and current.credential_id != credential_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este usuário.")
    credential = user_service.get_credential(db, credential_id)
    return user_service.user_to_dict(db, credential, include_private=True)


@router.put("/users/{credential_id}", response_model=UserResponse, summary="Atualizar usuário")
def update_user(
    credential_id: int,
    payload: UserUpdate,
    current: CurrentUserDep,
    db: Session = Depends(get_db),
):
    if current.role != "admin" and current.credential_id != credential_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este usuário.")
    if current.role != "admin" and payload.active is not None:
        raise HTTPException(status_code=403, detail="Usuário não pode alterar o próprio status de ativação.")
    return user_service.update_user(db, credential_id, payload)


@router.delete("/users/{credential_id}", status_code=204, summary="Excluir usuário")
def delete_user(
    credential_id: int,
    current: AdminDep,
    db: Session = Depends(get_db),
):
    user_service.delete_user(
        db,
        credential_id,
        current_admin_credential_id=current.credential_id,
    )
    return None
