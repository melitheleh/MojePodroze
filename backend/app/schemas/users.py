from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.db.models import User
from app.schemas.common import ApiModel, ShortName

Login = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=50, pattern=r"^[\w.-]+$"),
]
Password = Annotated[str, StringConstraints(min_length=4, max_length=128)]


class CredentialsIn(BaseModel):
    """Login i hasło. Uwaga: hasło jest zapisywane jawnym tekstem (uproszczenie projektu)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"login": "darek", "password": "tajne123"}]}
    )

    login: Login = Field(description="3–50 znaków: litery, cyfry, „_”, „.”, „-”.")
    password: Password


class UserOut(ApiModel):
    id: int = Field(description="Id użytkownika: frontend wysyła je w nagłówku X-User-Id.")
    login: str


class WeatherCity(BaseModel):
    name: ShortName
    country: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Kraków", "country": "Polska", "latitude": 50.06143, "longitude": 19.93658}
            ]
        }
    )


class UserProfileOut(BaseModel):
    id: int
    login: str
    weather_city: WeatherCity

    @classmethod
    def from_user(cls, user: User) -> Self:
        return cls(
            id=user.id,
            login=user.login,
            weather_city=WeatherCity(
                name=user.weather_city_name,
                country=user.weather_country,
                latitude=user.weather_latitude,
                longitude=user.weather_longitude,
            ),
        )
