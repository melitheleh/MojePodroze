from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.api.responses import UNAUTHORIZED, VALIDATION
from app.schemas.users import UserProfileOut, WeatherCity
from app.services import users as users_service

router = APIRouter(prefix="/users/me", tags=["Użytkownik"], responses=UNAUTHORIZED)


@router.get("", summary="Profil zalogowanego użytkownika", name="get_profile")
def get_profile(user: CurrentUser) -> UserProfileOut:
    return UserProfileOut.from_user(user)


@router.put(
    "/weather-city",
    summary="Zapisz miasto widżetu pogody",
    description=(
        "Miasto wybrane w widżecie (np. z wyników /api/weather/cities). Domyślnie Warszawa."
    ),
    responses=VALIDATION,
    name="set_weather_city",
)
def set_weather_city(payload: WeatherCity, user: CurrentUser, db: DbSession) -> UserProfileOut:
    return UserProfileOut.from_user(users_service.update_weather_city(db, user, payload))
