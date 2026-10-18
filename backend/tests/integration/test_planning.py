"""Plan dnia, lista „chcę odwiedzić”, lista pakowania i pamiętnik."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import ApiUser, add, create_trip

# --- Plan dnia ------------------------------------------------------------------------------


def test_plan_points_are_sorted_by_day_and_time(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    url = f"/api/trips/{trip['id']}/plan-points"
    add(
        client,
        user,
        trip["id"],
        "plan-points",
        {"day": "2027-05-02", "planned_time": "15:00", "place": "Kazimierz"},
    )
    add(
        client,
        user,
        trip["id"],
        "plan-points",
        {"day": "2027-05-02", "planned_time": "09:30", "place": "Wawel"},
    )
    add(client, user, trip["id"], "plan-points", {"day": "2027-05-01", "place": "Przyjazd"})
    points = client.get(url, headers=user.headers).json()
    assert [(p["day"], p["planned_time"], p["place"]) for p in points] == [
        ("2027-05-01", None, "Przyjazd"),
        ("2027-05-02", "09:30:00", "Wawel"),
        ("2027-05-02", "15:00:00", "Kazimierz"),
    ]


@pytest.mark.parametrize("day", ["2027-04-30", "2027-05-06"])
def test_plan_point_outside_trip_dates_is_rejected(
    client: TestClient, user: ApiUser, day: str
) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/plan-points",
        json={"day": day, "place": "Gdzieś"},
        headers=user.headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "DATE_OUTSIDE_TRIP"


def test_plan_point_cannot_be_moved_outside_trip(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    point = add(client, user, trip["id"], "plan-points", {"day": "2027-05-01", "place": "Rynek"})
    url = f"/api/trips/{trip['id']}/plan-points/{point['id']}"
    response = client.put(url, json={"day": "2027-06-01", "place": "Rynek"}, headers=user.headers)
    assert response.status_code == 422
    assert client.get(url, headers=user.headers).json()["day"] == "2027-05-01"


# --- Chcę odwiedzić -------------------------------------------------------------------------


def test_wishlist_item_can_be_ticked_off(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    item = add(client, user, trip["id"], "wishlist", {"name": "Kopiec Kraka", "note": "Zachód"})
    assert item["visited"] is False
    url = f"/api/trips/{trip['id']}/wishlist/{item['id']}"
    response = client.patch(url, json={"visited": True}, headers=user.headers)
    assert response.status_code == 200
    assert response.json() == {**item, "visited": True}


def test_wishlist_lists_unvisited_first(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    first = add(client, user, trip["id"], "wishlist", {"name": "A"})
    second = add(client, user, trip["id"], "wishlist", {"name": "B"})
    client.patch(
        f"/api/trips/{trip['id']}/wishlist/{first['id']}",
        json={"visited": True},
        headers=user.headers,
    )
    items = client.get(f"/api/trips/{trip['id']}/wishlist", headers=user.headers).json()
    assert [i["id"] for i in items] == [second["id"], first["id"]]


@pytest.mark.parametrize("body", [{"name": None}, {"visited": None}, {"name": ""}])
def test_wishlist_patch_rejects_empty_values(client: TestClient, user: ApiUser, body: dict) -> None:
    trip = create_trip(client, user)
    item = add(client, user, trip["id"], "wishlist", {"name": "A"})
    response = client.patch(
        f"/api/trips/{trip['id']}/wishlist/{item['id']}", json=body, headers=user.headers
    )
    assert response.status_code == 422


def test_wishlist_note_can_be_cleared(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    item = add(client, user, trip["id"], "wishlist", {"name": "A", "note": "B"})
    response = client.patch(
        f"/api/trips/{trip['id']}/wishlist/{item['id']}", json={"note": None}, headers=user.headers
    )
    assert response.json()["note"] is None
    assert response.json()["name"] == "A"


# --- Lista pakowania ------------------------------------------------------------------------


def test_packing_item_can_be_packed_and_renamed(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    item = add(client, user, trip["id"], "packing-items", {"name": "Krem z filtrem"})
    assert item["is_default"] is False
    url = f"/api/trips/{trip['id']}/packing-items/{item['id']}"
    packed = client.patch(url, json={"packed": True}, headers=user.headers).json()
    assert packed["packed"] is True
    renamed = client.patch(url, json={"name": "Krem SPF 50"}, headers=user.headers).json()
    assert renamed == {**packed, "name": "Krem SPF 50"}


def test_default_packing_item_can_be_deleted(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, trip_type="foreign")
    items = client.get(f"/api/trips/{trip['id']}/packing-items", headers=user.headers).json()
    response = client.delete(
        f"/api/trips/{trip['id']}/packing-items/{items[0]['id']}", headers=user.headers
    )
    assert response.status_code == 204
    remaining = client.get(f"/api/trips/{trip['id']}/packing-items", headers=user.headers).json()
    assert len(remaining) == 2


# --- Pamiętnik ------------------------------------------------------------------------------


def test_diary_entries_crud_and_order(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    url = f"/api/trips/{trip['id']}/diary-entries"
    second = add(
        client,
        user,
        trip["id"],
        "diary-entries",
        {"entry_date": "2027-05-02", "title": "Dzień 2", "content": "Wawel i smok"},
    )
    first = add(
        client,
        user,
        trip["id"],
        "diary-entries",
        {"entry_date": "2027-05-01", "content": "Przyjazd pociągiem"},
    )
    assert [e["id"] for e in client.get(url, headers=user.headers).json()] == [
        first["id"],
        second["id"],
    ]
    updated = client.put(
        f"{url}/{first['id']}",
        json={"entry_date": "2027-05-01", "title": "Start", "content": "Przyjazd"},
        headers=user.headers,
    )
    assert updated.json()["title"] == "Start"
    assert client.delete(f"{url}/{second['id']}", headers=user.headers).status_code == 204


def test_diary_entry_requires_content(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/diary-entries",
        json={"entry_date": "2027-05-01", "content": "   "},
        headers=user.headers,
    )
    assert response.status_code == 422
