from app.schemas.base import APIModel


class DashboardMetrics(APIModel):
    patients: int
    professionals: int
    administrators: int
    appointments: int
    scheduled: int
    cancelled: int
    done: int
    missed: int
    occupancy: int
    waitlist: int
    absence_rate: float
