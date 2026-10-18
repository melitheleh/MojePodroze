from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, Today
from app.api.responses import UNAUTHORIZED
from app.schemas.dashboard import DashboardOut
from app.services.insights import dashboard

router = APIRouter(prefix="/dashboard", tags=["Ekran główny"], responses=UNAUTHORIZED)


@router.get(
    "",
    summary="Ekran „Moje podróże”",
    description=(
        "Podróże pogrupowane w cztery statusy (w planie, w trakcie, zrealizowane, archiwum) "
        "oraz odliczanie do najbliższej podróży „w planie”. Pogoda i kursy walut mają osobne "
        "endpointy, żeby awaria zewnętrznego API nie psuła reszty ekranu."
    ),
    name="get_dashboard",
)
def get_dashboard(user: CurrentUser, db: DbSession, today: Today) -> DashboardOut:
    return dashboard(db, user, today)
