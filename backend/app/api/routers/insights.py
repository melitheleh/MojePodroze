from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, OwnedTrip
from app.api.responses import READ, UNAUTHORIZED
from app.domain.recommendations import DEFAULT_LIMIT, DEFAULT_MIN_RATING
from app.schemas.insights import RecommendationsOut, StatisticsOut, TripCostSummaryOut
from app.services import insights

router = APIRouter()


@router.get(
    "/trips/{trip_id}/cost-summary",
    tags=["Kosztorys i oceny"],
    summary="Kosztorys i ocena zbiorcza",
    description=(
        "Suma kosztów (PLN) i podział na sekcje, porównanie z budżetem (pozostało / "
        "przekroczono), poziom alertu budżetu (`ok` < 90% ≤ `warning` ≤ 100% < `exceeded`), "
        "ocena zbiorcza (zwykła średnia wszystkich ocen) i średnie sekcji. "
        "Liczone na bieżąco, nie są zapisywane w bazie."
    ),
    responses=READ,
    name="get_cost_summary",
)
def get_cost_summary(trip: OwnedTrip) -> TripCostSummaryOut:
    return insights.trip_cost_summary(trip)


@router.get(
    "/trips/{trip_id}/recommendations",
    tags=["Rekomendacje"],
    summary="Rekomendacje z wcześniejszych podróży do tego miasta",
    description=(
        "Najlepiej ocenione restauracje oraz noclegi i atrakcje z innych (rozpoczętych) "
        "podróży użytkownika do tego samego miasta, a także niezaliczone punkty z ich list "
        "„chcę odwiedzić” (bez tych, które są już na liście bieżącej podróży)."
    ),
    responses=READ,
    name="get_recommendations",
)
def get_recommendations(
    trip: OwnedTrip,
    user: CurrentUser,
    db: DbSession,
    min_rating: Annotated[
        Decimal, Query(ge=1, le=5, description="Minimalna średnia ocena.")
    ] = DEFAULT_MIN_RATING,
    limit: Annotated[
        int, Query(ge=1, le=20, description="Maks. pozycji w grupie.")
    ] = DEFAULT_LIMIT,
) -> RecommendationsOut:
    return insights.recommendations_for(db, user, trip, min_rating=min_rating, limit=limit)


@router.get(
    "/stats",
    tags=["Statystyki"],
    summary="Statystyki zbiorcze",
    description=(
        "Liczone z podróży zrealizowanych i archiwalnych: liczba podróży w roku, łączny "
        "i średni koszt, średni koszt dnia, porównanie kosztów według charakteru "
        "(np. góry vs morze)."
    ),
    responses=UNAUTHORIZED,
    name="get_statistics",
)
def get_statistics(user: CurrentUser, db: DbSession) -> StatisticsOut:
    return StatisticsOut.model_validate(insights.user_statistics(db, user))
