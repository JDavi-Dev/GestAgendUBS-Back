from typing import Literal

from pydantic import Field

from app.schemas.base import APIModel
from app.schemas.user import UserResponse

WaitlistPriority = Literal["alta", "media", "baixa"]
WaitlistStatus = Literal["aguardando", "alocado", "cancelado"]


class WaitlistJoin(APIModel):
    specialty: str = Field(min_length=2, max_length=100)
    patient_id: int | None = None


class WaitlistAllocate(APIModel):
    schedule_id: int


class WaitlistResponse(APIModel):
    id: int
    patient_id: int
    specialty: str
    priority: WaitlistPriority
    status: WaitlistStatus
    position: int | None = None
    created_at: str
    allocated_schedule_id: int | None = None
    allocated_appointment_id: int | None = None
    patient: UserResponse
