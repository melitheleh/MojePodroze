"""Widżety pogody i kursów walut z atrapami zewnętrznych API (także ich awaria)."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.fakes import FakeRatesClient, FakeWeatherClient
from tests.integration.helpers import ApiUser


def test_current_weather_for_default_city(
    client: TestClient, user: ApiUser, fake_weather: FakeWeatherClient
) -> None:
    response = client.get("/api/weather/current", headers=user.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["city"]["name"] == "Warszawa"
    assert body["weather"]["temperature_c"] == 14.3
    assert body["weather"]["description"] == "Pochmurno"
    assert fake_weather.weather_calls == [(52.22977, 21.01178)]


def test_weather_follows_city_chosen_in_widget(
    client: TestClient, user: ApiUser, fake_weather: FakeWeatherClient
) -> None:
    cities = client.get("/api/weather/cities", params={"query": "Krak"}, headers=user.headers)
    assert cities.status_code == 200
    krakow = cities.json()[0]
    assert krakow["name"] == "Kraków"
    city = {key: krakow[key] for key in ("name", "country", "latitude", "longitude")}
    client.put("/api/users/me/weather-city", json=city, headers=user.headers)

    body = client.get("/api/weather/current", headers=user.headers).json()
    assert body["city"]["name"] == "Kraków"
    assert fake_weather.weather_calls[-1] == (50.06143, 19.93658)


@pytest.mark.parametrize("params", [{"query": "K"}, {"query": "Kraków", "limit": 11}, {}])
def test_city_search_validates_query(client: TestClient, user: ApiUser, params: dict) -> None:
    response = client.get("/api/weather/cities", params=params, headers=user.headers)
    assert response.status_code == 422


def test_weather_outage_returns_503_but_rest_of_app_works(
    client: TestClient, user: ApiUser, fake_weather: FakeWeatherClient
) -> None:
    fake_weather.fail = True
    response = client.get("/api/weather/current", headers=user.headers)
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Serwis pogody jest chwilowo niedostępny.",
        "code": "EXTERNAL_API_UNAVAILABLE",
        "service": "Open-Meteo",
    }
    assert client.get("/api/weather/cities?query=Krak", headers=user.headers).status_code == 503
    assert client.get("/api/dashboard", headers=user.headers).status_code == 200
    assert client.get("/api/exchange-rates", headers=user.headers).status_code == 200


def test_exchange_rates_widget(client: TestClient, user: ApiUser) -> None:
    response = client.get("/api/exchange-rates", headers=user.headers)
    assert response.status_code == 200
    assert response.json() == {
        "table_no": "076/A/NBP/2027",
        "effective_date": "2027-04-19",
        "rates": [
            {"code": "EUR", "currency": "euro", "mid": 4.2954},
            {"code": "USD", "currency": "dolar amerykański", "mid": 3.9876},
            {"code": "GBP", "currency": "funt szterling", "mid": 5.0123},
        ],
    }


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [("100", "EUR", 429.54), ("1", "GBP", 5.01), ("0", "USD", 0), ("12.5", "USD", 49.85)],
)
def test_currency_calculator(
    client: TestClient, user: ApiUser, amount: str, currency: str, expected: float
) -> None:
    response = client.get(
        "/api/exchange-rates/convert",
        params={"amount": amount, "currency": currency},
        headers=user.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount_pln"] == expected
    assert body["currency"] == currency
    assert body["effective_date"] == "2027-04-19"


@pytest.mark.parametrize(
    "params",
    [
        {"amount": "-1", "currency": "EUR"},
        {"amount": "10", "currency": "CHF"},
        {"amount": "1.234", "currency": "EUR"},
        {"currency": "EUR"},
    ],
)
def test_currency_calculator_validation(client: TestClient, user: ApiUser, params: dict) -> None:
    response = client.get("/api/exchange-rates/convert", params=params, headers=user.headers)
    assert response.status_code == 422


def test_rates_outage_returns_503(
    client: TestClient, user: ApiUser, fake_rates: FakeRatesClient
) -> None:
    fake_rates.fail = True
    for url in ("/api/exchange-rates", "/api/exchange-rates/convert?amount=1&currency=EUR"):
        response = client.get(url, headers=user.headers)
        assert response.status_code == 503
        assert response.json()["service"] == "NBP"


@pytest.mark.parametrize(
    "url",
    [
        "/api/weather/current",
        "/api/weather/cities?query=Krak",
        "/api/exchange-rates",
        "/api/exchange-rates/convert?amount=1&currency=EUR",
    ],
)
def test_widgets_require_login(client: TestClient, url: str) -> None:
    assert client.get(url).status_code == 401
