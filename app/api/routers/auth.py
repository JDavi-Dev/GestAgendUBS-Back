from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import bearer
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse, summary="Autenticar usuário")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, payload.identifier, payload.password)


@router.post("/refresh", response_model=TokenResponse, summary="Renovar tokens")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh(db, payload.refresh_token)


@router.post("/logout", status_code=204, summary="Encerrar sessão")
def logout(
    payload: LogoutRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token de autenticação obrigatório.")
    auth_service.logout(db, credentials.credentials, payload.refresh_token)
    return None
