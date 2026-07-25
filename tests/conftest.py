import os
from dataclasses import dataclass
from datetime import date

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-more-than-thirty-two-characters"
os.environ["TIMEZONE"] = "America/Fortaleza"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.schemas.user import UserCreate
from app.services.users import create_user

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(TEST_ENGINE)
    Base.metadata.create_all(TEST_ENGINE)
    yield


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@dataclass
class Factory:
    def create_admin(
        self,
        *,
        email: str = "admin@test.com",
        password: str = "admin123",
        name: str = "Administrador Teste",
    ) -> dict:
        with TestingSessionLocal() as db:
            return create_user(
                db,
                UserCreate(
                    role="admin",
                    name=name,
                    email=email,
                    password=password,
                    position="Gestor",
                ),
            )

    def create_professional(
        self,
        *,
        email: str = "professional@test.com",
        password: str = "prof1234",
        name: str = "Profissional Teste",
        specialty: str = "Clínico Geral",
        council: str = "CRM-TEST-001",
        cpf: str | None = None,
    ) -> dict:
        with TestingSessionLocal() as db:
            return create_user(
                db,
                UserCreate(
                    role="professional",
                    name=name,
                    cpf=cpf,
                    email=email,
                    password=password,
                    specialty=specialty,
                    council=council,
                ),
            )

    def create_patient(
        self,
        *,
        cpf: str,
        email: str,
        password: str = "patient123",
        name: str = "Paciente Teste",
        birth_date: date = date(1990, 1, 1),
        priority_group: str = "nenhum",
    ) -> dict:
        with TestingSessionLocal() as db:
            return create_user(
                db,
                UserCreate(
                    role="patient",
                    name=name,
                    cpf=cpf,
                    email=email,
                    password=password,
                    birth_date=birth_date,
                    priority_group=priority_group,
                ),
            )


@pytest.fixture
def factory():
    return Factory()


@pytest.fixture
def auth_headers(client):
    def make(identifier: str, password: str) -> dict[str, str]:
        response = client.post(
            "/auth/login",
            json={"identifier": identifier, "password": password},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['accessToken']}"}

    return make
