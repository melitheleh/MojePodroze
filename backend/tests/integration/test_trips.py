"""CRUD podróży, izolacja danych użytkowników, typ podróży i lista pakowania."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import (
    ApiUser,
    add,
    create_trip,
    dictionary_id,
    flight_payload,
    trip_payload,
)


def test_create_trip_returns_full_resource(client: TestClient, user: ApiUser) -> None:
    payload = trip_payload(client, planned_budget=1234.56)
    response = client.post("/api/trips", json=payload, headers=user.headers)
    assert response.status_code == 201
    trip = response.json()
    assert trip["name"] == "Majówka w Krakowie"
    assert trip["status"] == "planned"
    assert trip["status_label"] == "w planie"
    assert trip["trip_type"] == "domestic"
    assert trip["character"]["code"] == "city"
    assert trip["planned_budget"] == 1234.56
    assert trip["duration_days"] == 5
    assert trip["allowed_transitions"] == ["in_progress"]
    assert trip["is_read_only"] is False
    assert trip["available_sections"] == ["transport", "meals", "places", "expenses"]


def test_foreign_trip_gets_default_packing_items(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, trip_type="foreign", destination_city="Rzym")
    assert "flights" in trip["available_sections"]
    items = client.get(f"/api/trips/{trip['id']}/packing-items", headers=user.headers).json()
    assert [(i["name"], i["is_default"], i["packed"]) for i in items] == [
        ("Paszport lub dowód osobisty", True, False),
        ("Ubezpieczenie podróżne", True, False),
        ("Przejściówka do gniazdka", True, False),
    ]


def test_domestic_trip_has_empty_packing_list(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    assert client.get(f"/api/trips/{trip['id']}/packing-items", headers=user.headers).json() == []


def test_end_date_before_start_is_rejected(client: TestClient, user: ApiUser) -> None:
    payload = trip_payload(client, start_date="2027-05-05", end_date="2027-05-01")
    response = client.post("/api/trips", json=payload, headers=user.headers)
    assert response.status_code == 422
    assert "Data zakończenia" in response.json()["errors"][0]["message"]


def test_unknown_character_is_rejected(client: TestClient, user: ApiUser) -> None:
    payload = trip_payload(client, character_id=999)
    response = client.post("/api/trips", json=payload, headers=user.headers)
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REFERENCE"


def test_list_contains_only_own_trips_sorted_by_date(
    client: TestClient, user: ApiUser, other_user: ApiUser
) -> None:
    later = create_trip(
        client, user, name="Później", start_date="2027-08-01", end_date="2027-08-02"
    )
    earlier = create_trip(client, user, name="Wcześniej")
    create_trip(client, other_user, name="Cudza")
    trips = client.get("/api/trips", headers=user.headers).json()
    assert [trip["id"] for trip in trips] == [earlier["id"], later["id"]]


def test_list_can_be_filtered_by_status(client: TestClient, user: ApiUser) -> None:
    planned = create_trip(client, user)
    started = create_trip(client, user, name="Trwa")
    client.post(
        f"/api/trips/{started['id']}/status", json={"status": "in_progress"}, headers=user.headers
    )
    in_progress = client.get("/api/trips?status=in_progress", headers=user.headers).json()
    assert [trip["id"] for trip in in_progress] == [started["id"]]
    planned_only = client.get("/api/trips", params={"status": "planned"}, headers=user.headers)
    assert [trip["id"] for trip in planned_only.json()] == [planned["id"]]


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("GET", "", None),
        ("PUT", "", "trip"),
        ("DELETE", "", None),
        ("POST", "/status", {"status": "in_progress"}),
        ("GET", "/cost-summary", None),
        ("GET", "/meals", None),
        (
            "POST",
            "/meals",
            {"dish": "x", "restaurant_name": "y", "meal_date": "2027-05-01", "cost": 1},
        ),
        ("GET", "/album", None),
        ("GET", "/recommendations", None),
    ],
)
def test_other_users_trip_is_invisible(
    client: TestClient,
    user: ApiUser,
    other_user: ApiUser,
    method: str,
    suffix: str,
    body: object,
) -> None:
    trip = create_trip(client, user)
    json_body = trip_payload(client) if body == "trip" else body
    response = client.request(
        method, f"/api/trips/{trip['id']}{suffix}", json=json_body, headers=other_user.headers
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Nie znaleziono podróży.", "code": "NOT_FOUND"}
    assert client.get(f"/api/trips/{trip['id']}", headers=user.headers).status_code == 200


def test_update_trip(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    payload = trip_payload(
        client,
        name="Weekend w górach",
        destination_city="Zakopane",
        character="mountains",
        planned_budget=None,
        end_date="2027-05-02",
    )
    response = client.put(f"/api/trips/{trip['id']}", json=payload, headers=user.headers)
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Weekend w górach"
    assert updated["character"]["code"] == "mountains"
    assert updated["planned_budget"] is None
    assert updated["duration_days"] == 2


def test_change_to_domestic_is_blocked_until_flights_are_removed(
    client: TestClient, user: ApiUser
) -> None:
    trip = create_trip(client, user, trip_type="foreign")
    flight = add(client, user, trip["id"], "flights", flight_payload())
    domestic = trip_payload(client, trip_type="domestic")

    blocked = client.put(f"/api/trips/{trip['id']}", json=domestic, headers=user.headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "TRIP_TYPE_CHANGE_BLOCKED"
    assert "Loty" in blocked.json()["detail"]
    assert client.get(f"/api/trips/{trip['id']}", headers=user.headers).json()["trip_type"] == (
        "foreign"
    )

    client.delete(f"/api/trips/{trip['id']}/flights/{flight['id']}", headers=user.headers)
    allowed = client.put(f"/api/trips/{trip['id']}", json=domestic, headers=user.headers)
    assert allowed.status_code == 200
    assert allowed.json()["trip_type"] == "domestic"


def test_change_to_foreign_adds_missing_packing_defaults(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    add(client, user, trip["id"], "packing-items", {"name": "ubezpieczenie PODRÓŻNE"})
    client.put(
        f"/api/trips/{trip['id']}",
        json=trip_payload(client, trip_type="foreign"),
        headers=user.headers,
    )
    names = [
        item["name"]
        for item in client.get(
            f"/api/trips/{trip['id']}/packing-items", headers=user.headers
        ).json()
    ]
    assert names == [
        "ubezpieczenie PODRÓŻNE",
        "Paszport lub dowód osobisty",
        "Przejściówka do gniazdka",
    ]


def test_delete_trip_removes_it_with_children(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    add(client, user, trip["id"], "diary-entries", {"entry_date": "2027-05-01", "content": "Hej"})
    response = client.delete(f"/api/trips/{trip['id']}", headers=user.headers)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/trips/{trip['id']}", headers=user.headers).status_code == 404


def test_trip_id_must_be_positive(client: TestClient, user: ApiUser) -> None:
    response = client.get("/api/trips/0", headers=user.headers)
    assert response.status_code == 422


def test_character_dictionary_lookup_helper(client: TestClient) -> None:
    assert dictionary_id(client, "trip_characters", "mountains") != dictionary_id(
        client, "trip_characters", "sea"
    )
