"""Klient Open-Meteo: wyszukiwanie miast (geocoding) i bieżąca pogoda. API nie wymaga klucza.

Parsowanie odpowiedzi jest w osobnych, czystych funkcjach, żeby testować je bez sieci.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.errors import ExternalServiceError

SERVICE_NAME = "Open-Meteo"
UNAVAILABLE_MESSAGE = "Serwis pogody jest chwilowo niedostępny."
INVALID_RESPONSE_MESSAGE = "Serwis pogody zwrócił nieprawidłowe dane."
UNKNOWN_WEATHER = "Nieznane warunki"
CURRENT_FIELDS = (
    "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day"
)

# Kody pogody WMO używane przez Open-Meteo.
WEATHER_CODES: dict[int, str] = {
    0: "Bezchmurnie",
    1: "Przeważnie bezchmurnie",
    2: "Częściowe zachmurzenie",
    3: "Pochmurno",
    45: "Mgła",
    48: "Mgła osadzająca szadź",
    51: "Lekka mżawka",
    53: "Umiarkowana mżawka",
    55: "Gęsta mżawka",
    56: "Lekka marznąca mżawka",
    57: "Gęsta marznąca mżawka",
    61: "Słaby deszcz",
    63: "Umiarkowany deszcz",
    65: "Silny deszcz",
    66: "Słaby marznący deszcz",
    67: "Silny marznący deszcz",
    71: "Słaby śnieg",
    73: "Umiarkowany śnieg",
    75: "Silny śnieg",
    77: "Ziarnisty śnieg",
    80: "Słabe przelotne opady deszczu",
    81: "Umiarkowane przelotne opady deszczu",
    82: "Gwałtowne przelotne opady deszczu",
    85: "Słabe przelotne opady śniegu",
    86: "Silne przelotne opady śniegu",
    95: "Burza",
    96: "Burza z gradem",
    99: "Burza z silnym gradem",
}


@dataclass(frozen=True)
class City:
    name: str
    country: str | None
    region: str | None
    latitude: float
    longitude: float


@dataclass(frozen=True)
class CurrentWeather:
    temperature_c: float
    apparent_temperature_c: float | None
    relative_humidity: int | None
    wind_speed_kmh: float | None
    weather_code: int
    description: str
    is_day: bool | None
    observed_at: str


def describe_weather_code(code: int) -> str:
    return WEATHER_CODES.get(code, UNKNOWN_WEATHER)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def parse_cities(payload: Any) -> list[City]:
    """Odpowiedź bez klucza ``results`` oznacza brak wyników (tak działa Open-Meteo)."""
    try:
        results = payload.get("results") or []
        return [
            City(
                name=str(result["name"]),
                country=result.get("country"),
                region=result.get("admin1"),
                latitude=float(result["latitude"]),
                longitude=float(result["longitude"]),
            )
            for result in results
        ]
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ExternalServiceError(SERVICE_NAME, INVALID_RESPONSE_MESSAGE) from exc


def parse_current_weather(payload: Any) -> CurrentWeather:
    try:
        current = payload["current"]
        code = int(current["weather_code"])
        is_day = current.get("is_day")
        return CurrentWeather(
            temperature_c=float(current["temperature_2m"]),
            apparent_temperature_c=_optional_float(current.get("apparent_temperature")),
            relative_humidity=_optional_int(current.get("relative_humidity_2m")),
            wind_speed_kmh=_optional_float(current.get("wind_speed_10m")),
            weather_code=code,
            description=describe_weather_code(code),
            is_day=None if is_day is None else bool(is_day),
            observed_at=str(current["time"]),
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ExternalServiceError(SERVICE_NAME, INVALID_RESPONSE_MESSAGE) from exc


class OpenMeteoClient:
    def __init__(self, http: httpx.Client, forecast_url: str, geocoding_url: str) -> None:
        self._http = http
        self._forecast_url = forecast_url
        self._geocoding_url = geocoding_url

    def search_cities(self, query: str, limit: int = 5) -> list[City]:
        params = {"name": query, "count": limit, "language": "pl", "format": "json"}
        return parse_cities(self._get_json(self._geocoding_url, params))

    def current_weather(self, latitude: float, longitude: float) -> CurrentWeather:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": CURRENT_FIELDS,
            "timezone": "auto",
            "wind_speed_unit": "kmh",
        }
        return parse_current_weather(self._get_json(self._forecast_url, params))

    def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        try:
            response = self._http.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalServiceError(SERVICE_NAME, UNAVAILABLE_MESSAGE) from exc
