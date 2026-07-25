from datetime import date
from typing import Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.schemas.base import APIModel
from app.utils.normalization import normalize_cpf, normalize_phone

Role = Literal["patient", "professional", "admin"]
PriorityGroup = Literal["nenhum", "idoso", "gestante", "pcd", "cadeirante"]


class PatientRegister(APIModel):
    name: str = Field(min_length=3, max_length=255)
    cpf: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    birth_date: date
    phone: str | None = None
    address: str | None = Field(default=None, max_length=500)
    priority_group: PriorityGroup = "nenhum"

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        return normalize_cpf(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Data de nascimento deve ser anterior à data atual.")
        return value


class UserCreate(APIModel):
    role: Role
    name: str = Field(min_length=3, max_length=255)
    cpf: str | None = None
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = Field(default=None, max_length=500)
    priority_group: PriorityGroup = "nenhum"
    specialty: str | None = Field(default=None, max_length=100)
    council: str | None = Field(default=None, max_length=80)
    position: str | None = Field(default=None, max_length=100)
    active: bool = True

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str | None) -> str | None:
        return normalize_cpf(value) if value else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @model_validator(mode="after")
    def validate_role_fields(self):
        if self.role == "patient":
            if not self.cpf or not self.birth_date:
                raise ValueError("Paciente deve informar CPF e data de nascimento.")
        elif self.role == "professional":
            if not self.specialty or not self.council:
                raise ValueError("Profissional deve informar especialidade e registro profissional.")
        return self


class UserUpdate(APIModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    cpf: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = Field(default=None, max_length=500)
    priority_group: PriorityGroup | None = None
    specialty: str | None = Field(default=None, max_length=100)
    council: str | None = Field(default=None, max_length=80)
    position: str | None = Field(default=None, max_length=100)
    active: bool | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str | None) -> str | None:
        return normalize_cpf(value) if value else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)


class UserResponse(APIModel):
    id: int
    role: Role
    name: str
    cpf: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    priority_group: PriorityGroup | None = None
    specialty: str | None = None
    council: str | None = None
    position: str | None = None
    active: bool = True
