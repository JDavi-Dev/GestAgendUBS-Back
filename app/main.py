from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import appointments, auth, dashboard, health, schedules, users, waitlist
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API REST do Sistema de Gestão de Agendamentos para Unidades Básicas de Saúde. "
        "Implementa autenticação JWT, CRUD de usuários, horários, agendamentos, fila de espera "
        "e indicadores gerenciais."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    location = ".".join(str(item) for item in first.get("loc", []) if item != "body")
    message = first.get("msg", "Dados inválidos.")
    detail = f"{location}: {message}" if location else message
    return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(schedules.router)
app.include_router(appointments.router)
app.include_router(waitlist.router)
app.include_router(dashboard.router)
