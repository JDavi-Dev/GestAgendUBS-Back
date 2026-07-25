from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Administrator, Appointment, Credential, Patient, Professional, Schedule, WaitlistEntry
from app.schemas.user import PatientRegister, UserCreate, UserUpdate

ROLE_MODEL = {
    "patient": Patient,
    "professional": Professional,
    "admin": Administrator,
}


def get_credential(db: Session, credential_id: int) -> Credential:
    credential = db.get(Credential, credential_id)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return credential


def find_credential_for_profile(db: Session, role: str, reference_id: int) -> Credential | None:
    return db.scalar(
        select(Credential).where(
            Credential.role == role,
            Credential.reference_id == reference_id,
        )
    )


def get_profile(db: Session, credential: Credential):
    model = ROLE_MODEL.get(credential.role)
    if model is None:
        raise HTTPException(status_code=500, detail="Perfil de usuário inválido.")
    profile = db.get(model, credential.reference_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil do usuário não encontrado.")
    return profile


def get_profile_by_public_id(db: Session, public_id: int, expected_role: str | None = None):
    credential = get_credential(db, public_id)
    if expected_role and credential.role != expected_role:
        raise HTTPException(status_code=404, detail="Usuário não encontrado para o perfil solicitado.")
    return credential, get_profile(db, credential)


def user_to_dict(db: Session, credential: Credential, *, include_private: bool = True) -> dict:
    profile = get_profile(db, credential)
    base = {
        "id": credential.id,
        "role": credential.role,
        "name": profile.name,
        "active": credential.active and getattr(profile, "active", True),
    }

    if credential.role == "patient":
        base.update(
            {
                "cpf": profile.cpf,
                "email": profile.email,
                "phone": profile.phone,
                "birthDate": profile.birth_date,
                "address": profile.address,
                "priorityGroup": profile.priority_group,
            }
        )
    elif credential.role == "professional":
        base.update(
            {
                "specialty": profile.specialty,
                "council": profile.council,
            }
        )
        if include_private:
            base.update({"cpf": profile.cpf, "email": profile.email, "phone": profile.phone})
    else:
        if include_private:
            base.update(
                {
                    "cpf": profile.cpf,
                    "email": profile.email,
                    "phone": profile.phone,
                    "position": profile.position,
                }
            )
    return base


def _create_patient(db: Session, data: PatientRegister | UserCreate) -> tuple[Credential, Patient]:
    patient = Patient(
        cpf=data.cpf,
        name=data.name,
        email=str(data.email).lower(),
        phone=data.phone,
        birth_date=data.birth_date,
        address=data.address,
        priority_group=data.priority_group,
    )
    db.add(patient)
    db.flush()
    credential = Credential(
        login=patient.cpf,
        password_hash=hash_password(data.password),
        role="patient",
        reference_id=patient.id,
        active=True,
    )
    db.add(credential)
    db.flush()
    return credential, patient


def register_patient(db: Session, data: PatientRegister) -> dict:
    try:
        credential, _ = _create_patient(db, data)
        db.commit()
        return user_to_dict(db, credential)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CPF, e-mail ou login já cadastrado.",
        ) from exc


def create_user(db: Session, data: UserCreate) -> dict:
    try:
        if data.role == "patient":
            credential, _ = _create_patient(db, data)
        elif data.role == "professional":
            professional = Professional(
                name=data.name,
                cpf=data.cpf,
                email=str(data.email).lower(),
                phone=data.phone,
                specialty=data.specialty,
                council=data.council,
                active=data.active,
            )
            db.add(professional)
            db.flush()
            credential = Credential(
                login=professional.email,
                password_hash=hash_password(data.password),
                role="professional",
                reference_id=professional.id,
                active=data.active,
            )
            db.add(credential)
            db.flush()
        else:
            administrator = Administrator(
                name=data.name,
                cpf=data.cpf,
                email=str(data.email).lower(),
                phone=data.phone,
                position=data.position,
                active=data.active,
            )
            db.add(administrator)
            db.flush()
            credential = Credential(
                login=administrator.email,
                password_hash=hash_password(data.password),
                role="admin",
                reference_id=administrator.id,
                active=data.active,
            )
            db.add(credential)
            db.flush()

        db.commit()
        return user_to_dict(db, credential)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CPF, e-mail, login ou registro profissional já cadastrado.",
        ) from exc


def list_users(db: Session, role: str, *, include_private: bool) -> list[dict]:
    if role not in ROLE_MODEL:
        raise HTTPException(status_code=422, detail="Perfil inválido.")
    credentials = db.scalars(
        select(Credential).where(Credential.role == role).order_by(Credential.id)
    ).all()
    return [user_to_dict(db, credential, include_private=include_private) for credential in credentials]


def update_user(db: Session, credential_id: int, data: UserUpdate) -> dict:
    credential = get_credential(db, credential_id)
    profile = get_profile(db, credential)
    changes = data.model_dump(exclude_unset=True)

    allowed_by_role = {
        "patient": {"name", "cpf", "email", "phone", "birth_date", "address", "priority_group", "password", "active"},
        "professional": {"name", "cpf", "email", "phone", "specialty", "council", "password", "active"},
        "admin": {"name", "cpf", "email", "phone", "position", "password", "active"},
    }
    invalid = set(changes) - allowed_by_role[credential.role]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Campos não permitidos para o perfil: {', '.join(sorted(invalid))}.")

    password = changes.pop("password", None)
    active = changes.pop("active", None)

    for field, value in changes.items():
        setattr(profile, field, value)

    if credential.role == "patient" and "cpf" in changes:
        credential.login = profile.cpf
    elif credential.role in {"professional", "admin"} and "email" in changes:
        credential.login = profile.email.lower()
        profile.email = profile.email.lower()

    if password:
        credential.password_hash = hash_password(password)
    if active is not None:
        credential.active = active
        if hasattr(profile, "active"):
            profile.active = active

    try:
        db.commit()
        return user_to_dict(db, credential)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CPF, e-mail, login ou registro profissional já utilizado.",
        ) from exc


def delete_user(db: Session, credential_id: int, *, current_admin_credential_id: int) -> None:
    credential = get_credential(db, credential_id)
    profile = get_profile(db, credential)

    if credential.role == "admin":
        if credential.id == current_admin_credential_id:
            raise HTTPException(status_code=409, detail="Não é permitido excluir a própria conta administrativa.")
        active_admins = db.scalar(
            select(func.count(Credential.id)).where(Credential.role == "admin", Credential.active.is_(True))
        ) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="O sistema deve manter pelo menos um administrador ativo.")

    if credential.role == "patient":
        linked = db.scalar(select(func.count(Appointment.id)).where(Appointment.patient_id == profile.id)) or 0
        waiting = db.scalar(select(func.count(WaitlistEntry.id)).where(WaitlistEntry.patient_id == profile.id)) or 0
        if linked or waiting:
            raise HTTPException(
                status_code=409,
                detail="Não é possível excluir paciente vinculado a agendamentos ou fila de espera.",
            )
    elif credential.role == "professional":
        linked = db.scalar(select(func.count(Schedule.id)).where(Schedule.professional_id == profile.id)) or 0
        if linked:
            raise HTTPException(status_code=409, detail="Não é possível excluir profissional vinculado a horários.")

    db.delete(credential)
    db.delete(profile)
    db.commit()
