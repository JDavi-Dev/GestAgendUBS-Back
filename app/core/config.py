from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas do ambiente/.env."""

    app_name: str = "SGA UBS API"
    app_version: str = "2.0.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    database_url: str = "sqlite:///./sga_ubs.db"
    jwt_secret_key: str = Field(default="change-this-secret-in-production-with-at-least-32-chars")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    refresh_token_expire_days: int = 30
    timezone: str = "America/Fortaleza"

    cors_origins: str = "http://localhost:5173,http://localhost:80,http://localhost"

    bootstrap_admin_name: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_cpf: str | None = None
    bootstrap_admin_phone: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY deve ter pelo menos 32 caracteres.")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
