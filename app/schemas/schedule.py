from __future__ import annotations

from datetime import date as DateType, time as TimeType
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import APIModel
from app.schemas.user import UserResponse

ScheduleStatus = Literal["available", "busy", "blocked"]


class ScheduleCreate(APIModel):
    professional_id: int
    specialty: str | None = Field(default=None, max_length=100)
    date: DateType
    start_time: TimeType
    end_time: TimeType
    status: ScheduleStatus = "available"

    @model_validator(mode="after")
    def validate_interval(self):
        if self.end_time <= self.start_time:
            raise ValueError("O horário final deve ser posterior ao horário inicial.")
        if self.date < DateType.today():
            raise ValueError("Não é permitido criar horário em data passada.")
        return self


class ScheduleUpdate(APIModel):
    professional_id: int | None = None
    specialty: str | None = Field(default=None, max_length=100)
    date: DateType | None = None
    start_time: TimeType | None = None
    end_time: TimeType | None = None
    status: ScheduleStatus | None = None


class ScheduleResponse(APIModel):
    id: int
    professional_id: int
    specialty: str
    date: DateType
    start_time: TimeType
    end_time: TimeType
    status: ScheduleStatus
    professional: UserResponse
