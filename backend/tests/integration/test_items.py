"""Pozycje kosztowe: pełny CRUD każdej sekcji i reguły sekcji zależne od typu podróży."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import (
    ApiUser,
    add,
    create_trip,
    expense_payload,
    flight_payload,
    meal_payload,
    place_payload,
    transport_payload,
)

# (ścieżka, fabryka danych, pole do edycji, nowa wartość)
SECTIONS: list[tuple[str, Callable[[TestClient], dict[str, Any]], str, Any]] = [
    ("flights", lambda _c: flight_payload(), "arrival_airport", "Mediolan (MXP)"),
    ("transports", transport_payload, "route_to", "Zakopane"),
    ("meals", lambda _c: meal_payload(), "restaurant_name", "Pod Wawelem"),
    ("places", lambda _c: place_payload(), "note", "Wrócić wiosną"),
    ("expenses", expense_payload, "description", "Pocztówki"),
]


@pytest.mark.parametrize(("path", "make_payload", "field", "new_value"), SECTIONS)
def test_crud_for_every_section(
    client: TestClient,
    user: ApiUser,
    path: str,
    make_payload: Callable[[TestClient], dict[str, Any]],
    field: str,
    new_value: Any,
) -> None:
    trip = create_trip(client, user, trip_type="foreign")
    base = f"/api/trips/{trip['id']}/{path}"
    payload = make_payload(client)

    created = add(client, user, trip["id"], path, payload)
    assert created["trip_id"] == trip["id"]
    assert created["cost"] == float(payload["cost"])

    assert client.get(base, headers=user.headers).json() == [created]
    assert client.get(f"{base}/{created['id']}", headers=user.headers).json() == created

    updated = client.put(
        f"{base}/{created['id']}", json={**payload, field: new_value}, headers=user.headers
    )
    assert updated.status_code == 200
    assert updated.json()[field] == new_value

    deleted = client.delete(f"{base}/{created['id']}", headers=user.headers)
    assert deleted.status_code == 204
    missing = client.get(f"{base}/{created['id']}", headers=user.headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


def test_flight_cannot_be_added_to_domestic_trip(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, trip_type="domestic")
    response = client.post(
        f"/api/trips/{trip['id']}/flights", json=flight_payload(), headers=user.headers
    )
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Sekcja „Loty” nie jest dostępna dla podróży typu „krajowa”.",
        "code": "SECTION_NOT_ALLOWED",
    }


def test_nested_dictionary_entries_are_returned(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    transport = add(client, user, trip["id"], "transports", transport_payload(client))
    expense = add(client, user, trip["id"], "expenses", expense_payload(client))
    assert transport["transport_mean"]["name"] == "Pociąg"
    assert expense["category"]["name"] == "Pamiątki"
    assert "rating" not in expense


def test_flight_number_is_upper_cased(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, trip_type="foreign")
    flight = add(client, user, trip["id"], "flights", flight_payload(flight_number=" fr 1234 "))
    assert flight["flight_number"] == "FR 1234"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"rating": 6}, "rating"),
        ({"rating": 0}, "rating"),
        ({"cost": -1}, "cost"),
        ({"cost": 10.555}, "cost"),
        ({"restaurant_name": ""}, "restaurant_name"),
        ({"meal_date": "2027-02-30"}, "meal_date"),
    ],
)
def test_invalid_item_data_is_rejected(
    client: TestClient, user: ApiUser, overrides: dict[str, Any], field: str
) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/meals", json=meal_payload(**overrides), headers=user.headers
    )
    assert response.status_code == 422
    assert field in [error["field"] for error in response.json()["errors"]]


def test_arrival_before_departure_is_rejected(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, trip_type="foreign")
    payload = flight_payload(arrival_at="2027-05-01T05:00:00")
    response = client.post(f"/api/trips/{trip['id']}/flights", json=payload, headers=user.headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("path", "make_payload", "message"),
    [
        ("transports", lambda c: transport_payload(c, transport_mean_id=999), "środek transportu"),
        ("expenses", lambda c: expense_payload(c, category_id=999), "kategoria wydatku"),
    ],
)
def test_unknown_dictionary_reference_is_rejected(
    client: TestClient,
    user: ApiUser,
    path: str,
    make_payload: Callable[[TestClient], dict[str, Any]],
    message: str,
) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/{path}", json=make_payload(client), headers=user.headers
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REFERENCE"
    assert message in response.json()["detail"]


def test_item_is_only_reachable_through_its_own_trip(client: TestClient, user: ApiUser) -> None:
    first = create_trip(client, user)
    second = create_trip(client, user, name="Druga")
    meal = add(client, user, first["id"], "meals", meal_payload())
    response = client.get(f"/api/trips/{second['id']}/meals/{meal['id']}", headers=user.headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Nie znaleziono posiłku."


def test_items_are_sorted_by_date(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    later = add(client, user, trip["id"], "meals", meal_payload(meal_date="2027-05-04"))
    earlier = add(client, user, trip["id"], "meals", meal_payload(meal_date="2027-05-02"))
    meals = client.get(f"/api/trips/{trip['id']}/meals", headers=user.headers).json()
    assert [meal["id"] for meal in meals] == [earlier["id"], later["id"]]


def test_rating_is_optional(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    place = add(client, user, trip["id"], "places", place_payload(rating=None, note=None))
    assert place["rating"] is None
    assert place["note"] is None
