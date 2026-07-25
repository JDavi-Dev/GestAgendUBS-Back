from typing import Literal

from pydantic import Field

from app.schemas.base import APIModel
from app.schemas.schedule import ScheduleResponse
from app.schemas.user import UserResponse

AppointmentStatus = Literal["scheduled", "cancelled", "done", "missed"]


class AppointmentCreate(APIModel):
    schedule_id: int
    patient_id: int | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentCancel(APIModel):
    reason: str | None = Field(default=None, max_length=255)


class AppointmentStatusUpdate(APIModel):
    status: Literal["done", "missed"]
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentResponse(APIModel):
    id: int
    patient_id: int
    schedule_id: int
    status: AppointmentStatus
    cancellation_reason: str | None = None
    notes: str | None = None
    created_at: str
    schedule: ScheduleResponse
    patient: UserResponse
    professional: UserResponse
