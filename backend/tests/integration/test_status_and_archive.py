"""Maszyna stanów przez API i reguła „archiwum tylko do odczytu”."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import (
    PNG_BYTES,
    ApiUser,
    add,
    create_trip,
    meal_payload,
    set_status,
    trip_payload,
)


def test_full_lifecycle_forward_and_back(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    body = set_status(client, user, trip["id"], "in_progress", "completed", "archived")
    assert body["status"] == "archived"
    assert body["is_read_only"] is True
    assert body["allowed_transitions"] == ["completed"]

    body = set_status(client, user, trip["id"], "completed", "in_progress", "planned")
    assert body["status"] == "planned"


@pytest.mark.parametrize("target", ["completed", "archived", "planned"])
def test_skipping_or_repeating_status_is_rejected(
    client: TestClient, user: ApiUser, target: str
) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/status", json={"status": target}, headers=user.headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"
    assert client.get(f"/api/trips/{trip['id']}", headers=user.headers).json()["status"] == (
        "planned"
    )


def test_unknown_status_is_validation_error(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/status", json={"status": "lost"}, headers=user.headers
    )
    assert response.status_code == 422


@pytest.fixture
def archived_trip(client: TestClient, user: ApiUser) -> dict:
    trip = create_trip(client, user)
    meal = add(client, user, trip["id"], "meals", meal_payload())
    wish = add(client, user, trip["id"], "wishlist", {"name": "Kopiec Kraka"})
    photo = client.post(
        f"/api/trips/{trip['id']}/photos",
        files={"file": ("a.png", PNG_BYTES, "image/png")},
        headers=user.headers,
    ).json()
    set_status(client, user, trip["id"], "in_progress", "completed", "archived")
    return {"trip": trip, "meal": meal, "wish": wish, "photo": photo}


def write_requests(client: TestClient, data: dict) -> list[tuple[str, str, dict | None]]:
    trip_id = data["trip"]["id"]
    return [
        ("PUT", f"/api/trips/{trip_id}", trip_payload(client)),
        ("DELETE", f"/api/trips/{trip_id}", None),
        ("POST", f"/api/trips/{trip_id}/meals", meal_payload()),
        ("PUT", f"/api/trips/{trip_id}/meals/{data['meal']['id']}", meal_payload(cost=1)),
        ("DELETE", f"/api/trips/{trip_id}/meals/{data['meal']['id']}", None),
        ("PATCH", f"/api/trips/{trip_id}/wishlist/{data['wish']['id']}", {"visited": True}),
        (
            "POST",
            f"/api/trips/{trip_id}/diary-entries",
            {"entry_date": "2027-05-01", "content": "x"},
        ),
        ("PATCH", f"/api/trips/{trip_id}/photos/{data['photo']['id']}", {"caption": "x"}),
        ("DELETE", f"/api/trips/{trip_id}/photos/{data['photo']['id']}", None),
    ]


def test_every_write_to_archived_trip_is_rejected(
    client: TestClient, user: ApiUser, archived_trip: dict
) -> None:
    for method, url, body in write_requests(client, archived_trip):
        response = client.request(method, url, json=body, headers=user.headers)
        assert response.status_code == 409, (method, url)
        assert response.json()["code"] == "TRIP_ARCHIVED", (method, url)


def test_photo_upload_to_archived_trip_is_rejected(
    client: TestClient, user: ApiUser, archived_trip: dict
) -> None:
    response = client.post(
        f"/api/trips/{archived_trip['trip']['id']}/photos",
        files={"file": ("b.png", PNG_BYTES, "image/png")},
        headers=user.headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "TRIP_ARCHIVED"


def test_archived_trip_is_still_readable(
    client: TestClient, user: ApiUser, archived_trip: dict
) -> None:
    trip_id = archived_trip["trip"]["id"]
    summary = client.get(f"/api/trips/{trip_id}/cost-summary", headers=user.headers).json()
    assert summary["is_read_only"] is True
    assert summary["total_cost"] == 42.5
    album = client.get(f"/api/trips/{trip_id}/album", headers=user.headers).json()
    assert len(album) == 1
    photo_id = archived_trip["photo"]["id"]
    file_response = client.get(f"/api/trips/{trip_id}/photos/{photo_id}/file", headers=user.headers)
    assert file_response.status_code == 200
    assert client.get(f"/api/trips/{trip_id}/meals", headers=user.headers).status_code == 200


def test_reverting_archive_to_completed_allows_edits_again(
    client: TestClient, user: ApiUser, archived_trip: dict
) -> None:
    trip_id = archived_trip["trip"]["id"]
    set_status(client, user, trip_id, "completed")
    response = client.post(f"/api/trips/{trip_id}/meals", json=meal_payload(), headers=user.headers)
    assert response.status_code == 201


def test_completed_trip_can_still_be_supplemented(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    set_status(client, user, trip["id"], "in_progress", "completed")
    add(client, user, trip["id"], "meals", meal_payload())
    add(client, user, trip["id"], "diary-entries", {"entry_date": "2027-05-05", "content": "Ok"})
