from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminDep
from app.schemas.dashboard import DashboardMetrics
from app.services.dashboard import get_metrics

router = APIRouter(prefix="/dashboard", tags=["Indicadores Gerenciais"])


@router.get("/metrics", response_model=DashboardMetrics, summary="Consultar indicadores gerenciais")
def metrics(_: AdminDep, db: Session = Depends(get_db)):
    return get_metrics(db)
