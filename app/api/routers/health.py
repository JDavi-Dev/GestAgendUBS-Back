from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["Saúde da API"])


@router.get("/", summary="Informações da API")
def root():
    return {
        "name": "SGA UBS API",
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
    }


@router.get("/health", summary="Verificar saúde da API")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "healthy"}
