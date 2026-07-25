from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Administrator, Appointment, Patient, Professional, Schedule, WaitlistEntry


def get_metrics(db: Session) -> dict:
    patients = db.scalar(select(func.count(Patient.id))) or 0
    professionals = db.scalar(select(func.count(Professional.id))) or 0
    administrators = db.scalar(select(func.count(Administrator.id))) or 0
    appointments = db.scalar(select(func.count(Appointment.id))) or 0
    scheduled = db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "scheduled")) or 0
    cancelled = db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "cancelled")) or 0
    done = db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "done")) or 0
    missed = db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "missed")) or 0
    available = db.scalar(select(func.count(Schedule.id)).where(Schedule.status == "available")) or 0
    busy = db.scalar(select(func.count(Schedule.id)).where(Schedule.status == "busy")) or 0
    waitlist = db.scalar(
        select(func.count(WaitlistEntry.id)).where(WaitlistEntry.status == "aguardando")
    ) or 0

    schedulable_total = available + busy
    occupancy = round((busy / schedulable_total) * 100) if schedulable_total else 0
    attended_total = done + missed
    absence_rate = round((missed / attended_total) * 100, 2) if attended_total else 0.0

    return {
        "patients": patients,
        "professionals": professionals,
        "administrators": administrators,
        "appointments": appointments,
        "scheduled": scheduled,
        "cancelled": cancelled,
        "done": done,
        "missed": missed,
        "occupancy": occupancy,
        "waitlist": waitlist,
        "absenceRate": absence_rate,
    }
