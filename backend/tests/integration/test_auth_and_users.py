"""Rejestracja, logowanie, nagłówek X-User-Id i profil użytkownika."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import Settings
from tests.integration.helpers import ApiUser, register_user


def test_register_returns_id_and_login_without_password(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={"login": "ania", "password": "haslo123"})
    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "login": "ania"}


def test_password_is_stored_as_plain_text(client: TestClient, settings: Settings) -> None:
    """Dokumentuje świadome uproszczenie projektu (patrz README)."""
    register_user(client, "ania", "tajne123")
    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        stored = connection.execute(text("SELECT password FROM users WHERE login='ania'")).scalar()
    engine.dispose()
    assert stored == "tajne123"


def test_duplicate_login_is_rejected(client: TestClient, user: ApiUser) -> None:
    response = client.post("/api/auth/register", json={"login": "ania", "password": "inne123"})
    assert response.status_code == 409
    assert response.json()["code"] == "LOGIN_TAKEN"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"login": "ab", "password": "haslo123"}, "login"),
        ({"login": "z spacja", "password": "haslo123"}, "login"),
        ({"login": "ania", "password": "123"}, "password"),
        ({"password": "haslo123"}, "login"),
    ],
)
def test_register_validation_errors_point_to_field(
    client: TestClient, payload: dict, field: str
) -> None:
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"] == "Nieprawidłowe dane wejściowe."
    assert field in [error["field"] for error in body["errors"]]


def test_login_returns_the_same_user_id(client: TestClient, user: ApiUser) -> None:
    response = client.post("/api/auth/login", json={"login": "ania", "password": "haslo123"})
    assert response.status_code == 200
    assert response.json() == {"id": user.id, "login": "ania"}


def test_login_works_with_polish_characters_in_password(client: TestClient) -> None:
    register_user(client, "zosia", "zażółć gęślą")
    response = client.post("/api/auth/login", json={"login": "zosia", "password": "zażółć gęślą"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("login", "password"),
    [("ania", "zle-haslo"), ("nieznany", "haslo123"), ("ANIA", "haslo123")],
)
def test_login_with_wrong_credentials_is_rejected(
    client: TestClient, user: ApiUser, login: str, password: str
) -> None:
    response = client.post("/api/auth/login", json={"login": login, "password": password})
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Nieprawidłowy login lub hasło.",
        "code": "INVALID_CREDENTIALS",
    }


def test_missing_user_header_gives_401(client: TestClient) -> None:
    response = client.get("/api/trips")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("header", ["abc", "999999", "-1", "1.5"])
def test_invalid_user_header_gives_401(client: TestClient, user: ApiUser, header: str) -> None:
    response = client.get("/api/trips", headers={"X-User-Id": header})
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_USER"


def test_blank_user_header_gives_401(client: TestClient) -> None:
    response = client.get("/api/trips", headers={"X-User-Id": "  "})
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_profile_has_warsaw_as_default_weather_city(client: TestClient, user: ApiUser) -> None:
    response = client.get("/api/users/me", headers=user.headers)
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "login": "ania",
        "weather_city": {
            "name": "Warszawa",
            "country": "Polska",
            "latitude": 52.22977,
            "longitude": 21.01178,
        },
    }


def test_weather_city_can_be_changed(client: TestClient, user: ApiUser) -> None:
    city = {"name": "Kraków", "country": "Polska", "latitude": 50.06143, "longitude": 19.93658}
    response = client.put("/api/users/me/weather-city", json=city, headers=user.headers)
    assert response.status_code == 200
    assert response.json()["weather_city"] == city
    assert client.get("/api/users/me", headers=user.headers).json()["weather_city"] == city


@pytest.mark.parametrize(
    "city",
    [
        {"name": "X", "latitude": 91, "longitude": 0},
        {"name": "X", "latitude": 0, "longitude": -181},
        {"name": "", "latitude": 0, "longitude": 0},
    ],
)
def test_invalid_weather_city_is_rejected(client: TestClient, user: ApiUser, city: dict) -> None:
    response = client.put("/api/users/me/weather-city", json=city, headers=user.headers)
    assert response.status_code == 422
