from datetime import date, timedelta, time

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Credential, Patient, Professional, Schedule
from app.schemas.user import UserCreate
from app.services.users import create_user


def ensure_patient(db):
    credential = db.scalar(select(Credential).where(Credential.login == "12345678900"))
    if credential:
        return credential
    patient = Patient(
        cpf="12345678900",
        name="Paciente Demonstração",
        email="paciente@sgaubs.com",
        phone="83999999999",
        birth_date=date(1990, 5, 15),
        address="Endereço de demonstração",
        priority_group="nenhum",
    )
    db.add(patient)
    db.flush()
    credential = Credential(
        login=patient.cpf,
        password_hash=hash_password("paciente123"),
        role="patient",
        reference_id=patient.id,
        active=True,
    )
    db.add(credential)
    db.commit()
    return credential


def ensure_professional(db):
    login = "professional@sgaubs.com"
    credential = db.scalar(select(Credential).where(Credential.login == login))
    if credential:
        return credential
    professional = Professional(
        name="Profissional Demonstração",
        cpf=None,
        email=login,
        phone="83988888888",
        specialty="Clínico Geral",
        council="CRM-DEMO-001",
        active=True,
    )
    db.add(professional)
    db.flush()
    credential = Credential(
        login=login,
        password_hash=hash_password("prof123"),
        role="professional",
        reference_id=professional.id,
        active=True,
    )
    db.add(credential)
    db.commit()
    return credential


def ensure_schedules(db, professional_credential):
    professional = db.get(Professional, professional_credential.reference_id)
    for days, start in [(2, time(8, 0)), (2, time(9, 0)), (3, time(14, 0))]:
        schedule_date = date.today() + timedelta(days=days)
        exists = db.scalar(
            select(Schedule.id).where(
                Schedule.professional_id == professional.id,
                Schedule.date == schedule_date,
                Schedule.start_time == start,
            )
        )
        if not exists:
            db.add(
                Schedule(
                    professional_id=professional.id,
                    specialty=professional.specialty,
                    date=schedule_date,
                    start_time=start,
                    end_time=time(start.hour + 1, 0),
                    status="available",
                )
            )
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        ensure_patient(db)
        professional = ensure_professional(db)
        ensure_schedules(db, professional)
    print("Dados de demonstração verificados com sucesso.")


if __name__ == "__main__":
    main()
