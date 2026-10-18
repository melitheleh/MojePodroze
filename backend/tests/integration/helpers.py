"""Pomocnicze funkcje testów integracyjnych: logowanie i budowanie danych przez API."""

from dataclasses import dataclass
from datetime import date
from typing import Any

from fastapi.testclient import TestClient

FROZEN_TODAY = date(2027, 4, 20)  # „dzisiaj” w testach (podmieniane get_today)
MAX_UPLOAD_BYTES = 50 * 1024  # limit uploadu w testach

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@dataclass(frozen=True)
class ApiUser:
    id: int
    login: str

    @property
    def headers(self) -> dict[str, str]:
        return {"X-User-Id": str(self.id)}


def register_user(client: TestClient, login: str, password: str = "haslo123") -> ApiUser:
    response = client.post("/api/auth/register", json={"login": login, "password": password})
    assert response.status_code == 201, response.text
    body = response.json()
    return ApiUser(id=body["id"], login=body["login"])


def dictionary_id(client: TestClient, dictionary: str, code: str) -> int:
    entries = client.get("/api/dictionaries").json()[dictionary]
    return next(entry["id"] for entry in entries if entry["code"] == code)


def trip_payload(client: TestClient, **overrides: Any) -> dict[str, Any]:
    character = overrides.pop("character", "city")
    payload = {
        "name": "Majówka w Krakowie",
        "destination_city": "Kraków",
        "destination_country": "Polska",
        "start_date": "2027-05-01",
        "end_date": "2027-05-05",
        "trip_type": "domestic",
        "character_id": dictionary_id(client, "trip_characters", character),
        "planned_budget": 3000,
    }
    payload.update(overrides)
    return payload


def create_trip(client: TestClient, user: ApiUser, **overrides: Any) -> dict[str, Any]:
    response = client.post(
        "/api/trips", json=trip_payload(client, **overrides), headers=user.headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_status(client: TestClient, user: ApiUser, trip_id: int, *statuses: str) -> dict[str, Any]:
    """Przeprowadza podróż przez kolejne statusy (każdy krok musi się udać)."""
    body: dict[str, Any] = {}
    for status in statuses:
        response = client.post(
            f"/api/trips/{trip_id}/status", json={"status": status}, headers=user.headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
    return body


def add(
    client: TestClient, user: ApiUser, trip_id: int, path: str, payload: dict[str, Any]
) -> dict:
    response = client.post(f"/api/trips/{trip_id}/{path}", json=payload, headers=user.headers)
    assert response.status_code == 201, response.text
    return response.json()


def flight_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "flight_number": "LO327",
        "departure_airport": "Warszawa (WAW)",
        "arrival_airport": "Rzym (FCO)",
        "departure_at": "2027-05-01T06:30:00",
        "arrival_at": "2027-05-01T09:00:00",
        "cost": 850,
        "rating": 4,
        **overrides,
    }


def transport_payload(client: TestClient, **overrides: Any) -> dict[str, Any]:
    return {
        "transport_mean_id": dictionary_id(client, "transport_means", "train"),
        "route_from": "Warszawa",
        "route_to": "Kraków",
        "travel_date": "2027-05-01",
        "cost": 129.99,
        "rating": 5,
        **overrides,
    }


def meal_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "dish": "Pierogi ruskie",
        "restaurant_name": "Przystanek Pierogarnia",
        "meal_date": "2027-05-02",
        "cost": 42.5,
        "rating": 5,
        **overrides,
    }


def place_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "name": "Wawel",
        "kind": "attraction",
        "visit_date": "2027-05-02",
        "cost": 70,
        "rating": 5,
        "note": "Warto kupić bilety online",
        **overrides,
    }


def expense_payload(client: TestClient, **overrides: Any) -> dict[str, Any]:
    return {
        "category_id": dictionary_id(client, "expense_categories", "souvenirs"),
        "description": "Magnes na lodówkę",
        "expense_date": "2027-05-03",
        "cost": 15,
        **overrides,
    }
