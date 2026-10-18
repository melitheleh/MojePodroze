"""Parsowanie odpowiedzi Open-Meteo i klient HTTP (bez sieci: httpx.MockTransport)."""

import json
from typing import Any

import httpx
import pytest

from app.integrations.errors import ExternalServiceError
from app.integrations.open_meteo import (
    UNKNOWN_WEATHER,
    City,
    OpenMeteoClient,
    describe_weather_code,
    parse_cities,
    parse_current_weather,
)

GEOCODING_RESPONSE = {
    "results": [
        {
            "id": 3094802,
            "name": "Kraków",
            "latitude": 50.06143,
            "longitude": 19.93658,
            "country": "Polska",
            "admin1": "Małopolskie",
        },
        {"id": 1, "name": "Krakow", "latitude": 43.5, "longitude": -89.1},
    ],
    "generationtime_ms": 0.5,
}

FORECAST_RESPONSE = {
    "latitude": 52.23,
    "longitude": 21.01,
    "current_units": {"temperature_2m": "°C"},
    "current": {
        "time": "2027-04-20T12:00",
        "interval": 900,
        "temperature_2m": 14.3,
        "apparent_temperature": 12.9,
        "relative_humidity_2m": 61,
        "weather_code": 3,
        "wind_speed_10m": 11.5,
        "is_day": 1,
    },
}


def test_parse_cities_maps_fields() -> None:
    cities = parse_cities(GEOCODING_RESPONSE)
    assert cities[0] == City("Kraków", "Polska", "Małopolskie", 50.06143, 19.93658)
    assert cities[1].country is None
    assert cities[1].region is None


@pytest.mark.parametrize("payload", [{"generationtime_ms": 0.3}, {"results": None}, {}])
def test_parse_cities_without_results_returns_empty_list(payload: dict[str, Any]) -> None:
    assert parse_cities(payload) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"results": [{"name": "X"}]},  # brak współrzędnych
        {"results": [{"name": "X", "latitude": "abc", "longitude": 1}]},
        ["nie", "słownik"],
        None,
    ],
)
def test_parse_cities_rejects_invalid_payload(payload: Any) -> None:
    with pytest.raises(ExternalServiceError) as error:
        parse_cities(payload)
    assert error.value.service == "Open-Meteo"


def test_parse_current_weather() -> None:
    weather = parse_current_weather(FORECAST_RESPONSE)
    assert weather.temperature_c == 14.3
    assert weather.apparent_temperature_c == 12.9
    assert weather.relative_humidity == 61
    assert weather.wind_speed_kmh == 11.5
    assert weather.weather_code == 3
    assert weather.description == "Pochmurno"
    assert weather.is_day is True
    assert weather.observed_at == "2027-04-20T12:00"


def test_parse_current_weather_with_only_required_fields() -> None:
    payload = {"current": {"time": "2027-01-01T00:00", "temperature_2m": -3, "weather_code": 71}}
    weather = parse_current_weather(payload)
    assert weather.temperature_c == -3.0
    assert weather.apparent_temperature_c is None
    assert weather.relative_humidity is None
    assert weather.wind_speed_kmh is None
    assert weather.is_day is None
    assert weather.description == "Słaby śnieg"


def test_is_day_zero_means_night() -> None:
    payload = json.loads(json.dumps(FORECAST_RESPONSE))
    payload["current"]["is_day"] = 0
    assert parse_current_weather(payload).is_day is False


@pytest.mark.parametrize(
    "payload",
    [{}, {"current": {}}, {"current": {"temperature_2m": 1, "time": "t"}}, None],
)
def test_parse_current_weather_rejects_invalid_payload(payload: Any) -> None:
    with pytest.raises(ExternalServiceError):
        parse_current_weather(payload)


@pytest.mark.parametrize(
    ("code", "description"),
    [(0, "Bezchmurnie"), (61, "Słaby deszcz"), (95, "Burza"), (1234, UNKNOWN_WEATHER)],
)
def test_describe_weather_code(code: int, description: str) -> None:
    assert describe_weather_code(code) == description


# --- Klient HTTP z atrapą transportu --------------------------------------------------------


def make_client(handler: Any) -> OpenMeteoClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenMeteoClient(http, "https://forecast.test/v1", "https://geo.test/v1/search")


def test_search_cities_sends_query_parameters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=GEOCODING_RESPONSE)

    cities = make_client(handler).search_cities("Krak", limit=3)
    assert [c.name for c in cities] == ["Kraków", "Krakow"]
    params = requests[0].url.params
    assert requests[0].url.host == "geo.test"
    assert params["name"] == "Krak"
    assert params["count"] == "3"
    assert params["language"] == "pl"


def test_current_weather_requests_coordinates() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=FORECAST_RESPONSE)

    weather = make_client(handler).current_weather(52.23, 21.01)
    assert weather.description == "Pochmurno"
    params = requests[0].url.params
    assert params["latitude"] == "52.23"
    assert params["longitude"] == "21.01"
    assert "temperature_2m" in params["current"]


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500, text="błąd"), httpx.Response(200, text="to nie JSON")],
)
def test_client_wraps_http_errors(response: httpx.Response) -> None:
    with pytest.raises(ExternalServiceError) as error:
        make_client(lambda _request: response).current_weather(1, 1)
    assert "niedostępny" in error.value.message


def test_client_wraps_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("brak internetu", request=request)

    with pytest.raises(ExternalServiceError):
        make_client(handler).search_cities("Kraków")
