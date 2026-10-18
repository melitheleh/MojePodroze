"""Upload zdjęć na dysk, album według dni, pobieranie pliku i izolacja danych."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from tests.integration.helpers import (
    FROZEN_TODAY,
    JPEG_BYTES,
    MAX_UPLOAD_BYTES,
    PNG_BYTES,
    ApiUser,
    create_trip,
)


def upload(
    client: TestClient,
    user: ApiUser,
    trip_id: int,
    content: bytes = PNG_BYTES,
    filename: str = "zdjecie.png",
    **form: str,
):
    return client.post(
        f"/api/trips/{trip_id}/photos",
        files={"file": (filename, content, "image/png")},
        data=form,
        headers=user.headers,
    )


def test_upload_stores_file_and_defaults_day_to_today(
    client: TestClient, user: ApiUser, settings: Settings
) -> None:
    trip = create_trip(client, user)
    response = upload(client, user, trip["id"], caption="  Smok wawelski ")
    assert response.status_code == 201
    photo = response.json()
    assert photo["day"] == FROZEN_TODAY.isoformat()
    assert photo["caption"] == "Smok wawelski"
    assert photo["original_filename"] == "zdjecie.png"
    assert photo["content_type"] == "image/png"
    assert photo["size_bytes"] == len(PNG_BYTES)
    assert photo["file_url"] == f"/api/trips/{trip['id']}/photos/{photo['id']}/file"
    stored_files = list(Path(settings.upload_dir).rglob("*.png"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == PNG_BYTES


def test_file_endpoint_returns_image(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    photo = upload(client, user, trip["id"], content=JPEG_BYTES, filename="a.jpg").json()
    assert photo["content_type"] == "image/jpeg"  # wg zawartości, nie nagłówka klienta
    response = client.get(photo["file_url"], headers=user.headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEG_BYTES


def test_album_groups_photos_by_day(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    day2 = upload(client, user, trip["id"], day="2027-05-02").json()
    day1a = upload(client, user, trip["id"], day="2027-05-01").json()
    day1b = upload(client, user, trip["id"], day="2027-05-01").json()
    album = client.get(f"/api/trips/{trip['id']}/album", headers=user.headers).json()
    assert [(d["day"], [p["id"] for p in d["photos"]]) for d in album] == [
        ("2027-05-01", [day1a["id"], day1b["id"]]),
        ("2027-05-02", [day2["id"]]),
    ]
    listed = client.get(f"/api/trips/{trip['id']}/photos", headers=user.headers).json()
    assert [p["id"] for p in listed] == [day1a["id"], day1b["id"], day2["id"]]


def test_photo_day_and_caption_can_be_changed(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    photo = upload(client, user, trip["id"]).json()
    url = f"/api/trips/{trip['id']}/photos/{photo['id']}"
    response = client.patch(
        url, json={"day": "2027-05-03", "caption": "Rynek"}, headers=user.headers
    )
    assert response.status_code == 200
    assert response.json()["day"] == "2027-05-03"
    assert client.get(url, headers=user.headers).json()["caption"] == "Rynek"
    assert client.patch(url, json={"day": None}, headers=user.headers).status_code == 422


def test_non_image_is_rejected(client: TestClient, user: ApiUser, settings: Settings) -> None:
    trip = create_trip(client, user)
    response = upload(client, user, trip["id"], content=b"%PDF-1.7 dokument", filename="a.png")
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_UPLOAD"
    assert not list(Path(settings.upload_dir).rglob("*.*"))


def test_empty_file_is_rejected(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    response = upload(client, user, trip["id"], content=b"")
    assert response.status_code == 422


def test_too_large_file_is_rejected(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    content = PNG_BYTES + b"\x00" * MAX_UPLOAD_BYTES
    response = upload(client, user, trip["id"], content=content)
    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"


def test_missing_file_field_is_validation_error(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    response = client.post(
        f"/api/trips/{trip['id']}/photos", data={"caption": "x"}, headers=user.headers
    )
    assert response.status_code == 422
    assert "file" in [error["field"] for error in response.json()["errors"]]


def test_delete_photo_removes_file(client: TestClient, user: ApiUser, settings: Settings) -> None:
    trip = create_trip(client, user)
    photo = upload(client, user, trip["id"]).json()
    response = client.delete(f"/api/trips/{trip['id']}/photos/{photo['id']}", headers=user.headers)
    assert response.status_code == 204
    assert not list(Path(settings.upload_dir).rglob("*.png"))
    assert client.get(photo["file_url"], headers=user.headers).status_code == 404


def test_deleting_trip_removes_photo_files(
    client: TestClient, user: ApiUser, settings: Settings
) -> None:
    trip = create_trip(client, user)
    upload(client, user, trip["id"])
    upload(client, user, trip["id"])
    client.delete(f"/api/trips/{trip['id']}", headers=user.headers)
    assert not list(Path(settings.upload_dir).rglob("*.png"))


def test_other_user_cannot_download_photo(
    client: TestClient, user: ApiUser, other_user: ApiUser
) -> None:
    trip = create_trip(client, user)
    photo = upload(client, user, trip["id"]).json()
    assert client.get(photo["file_url"], headers=other_user.headers).status_code == 404
    assert client.get(photo["file_url"]).status_code == 401


def test_photo_of_another_trip_is_not_found(client: TestClient, user: ApiUser) -> None:
    first = create_trip(client, user)
    second = create_trip(client, user, name="Druga")
    photo = upload(client, user, first["id"]).json()
    response = client.get(f"/api/trips/{second['id']}/photos/{photo['id']}", headers=user.headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Nie znaleziono zdjęcia."
