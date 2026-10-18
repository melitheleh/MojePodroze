"""Typ kolumny Money (grosze w INTEGER) i zapis zdjęć na dysku (katalog tymczasowy)."""

import io
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.dialects import sqlite

from app.core.errors import FileTooLargeError, InvalidUploadError, NotFoundError
from app.db.types import Money
from app.services.photo_storage import PhotoStorage, detect_image_type

DIALECT = sqlite.dialect()
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32

# --- Money ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "stored"),
    [
        (Decimal("12.34"), 1234),
        (Decimal("0"), 0),
        (Decimal("0.005"), 1),  # połówka grosza w górę
        (Decimal("19.99"), 1999),
        (10, 1000),
        (None, None),
    ],
)
def test_money_is_stored_as_grosze(value: Decimal | int | None, stored: int | None) -> None:
    assert Money().process_bind_param(value, DIALECT) == stored


@pytest.mark.parametrize(
    ("stored", "value"),
    [(1234, Decimal("12.34")), (0, Decimal("0.00")), (5, Decimal("0.05")), (None, None)],
)
def test_money_is_read_as_decimal(stored: int | None, value: Decimal | None) -> None:
    result = Money().process_result_value(stored, DIALECT)
    assert result == value
    if value is not None:
        assert result.as_tuple().exponent == -2


# --- Rozpoznawanie formatu ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "kind"),
    [
        (JPEG, "jpg"),
        (PNG, "png"),
        (b"GIF87a" + b"\x00" * 6, "gif"),
        (b"GIF89a" + b"\x00" * 6, "gif"),
        (b"RIFF\x00\x00\x00\x00WEBP", "webp"),
        (b"RIFF\x00\x00\x00\x00WAVE", None),
        (b"%PDF-1.7", None),
        (b"<svg></svg>", None),
        (b"", None),
    ],
)
def test_detect_image_type_by_magic_bytes(header: bytes, kind: str | None) -> None:
    assert detect_image_type(header) == kind


# --- PhotoStorage ---------------------------------------------------------------------------


@pytest.fixture
def storage(tmp_path: Path) -> PhotoStorage:
    return PhotoStorage(tmp_path, max_bytes=100)


def test_save_writes_file_under_trip_directory(storage: PhotoStorage, tmp_path: Path) -> None:
    stored = storage.save(7, io.BytesIO(PNG))
    assert stored.filename.startswith("trip_7/")
    assert stored.filename.endswith(".png")
    assert stored.media_type == "image/png"
    assert stored.size_bytes == len(PNG)
    assert (tmp_path / stored.filename).read_bytes() == PNG


def test_each_upload_gets_unique_name(storage: PhotoStorage) -> None:
    assert storage.save(1, io.BytesIO(JPEG)).filename != storage.save(1, io.BytesIO(JPEG)).filename


def test_file_at_size_limit_is_accepted(storage: PhotoStorage) -> None:
    data = JPEG + b"\x00" * (100 - len(JPEG))
    assert storage.save(1, io.BytesIO(data)).size_bytes == 100


def test_too_large_file_is_rejected(storage: PhotoStorage) -> None:
    data = JPEG + b"\x00" * (101 - len(JPEG))
    with pytest.raises(FileTooLargeError):
        storage.save(1, io.BytesIO(data))


def test_empty_file_is_rejected(storage: PhotoStorage) -> None:
    with pytest.raises(InvalidUploadError, match="pusty"):
        storage.save(1, io.BytesIO(b""))


def test_non_image_is_rejected(storage: PhotoStorage) -> None:
    with pytest.raises(InvalidUploadError, match="JPG"):
        storage.save(1, io.BytesIO(b"to jest tekst, nie zdjecie"))


def test_path_for_returns_existing_file(storage: PhotoStorage) -> None:
    stored = storage.save(1, io.BytesIO(PNG))
    assert storage.path_for(stored.filename).read_bytes() == PNG


@pytest.mark.parametrize("filename", ["../secret.txt", "trip_1/missing.png", "../../etc/passwd"])
def test_path_for_rejects_missing_or_outside_files(
    storage: PhotoStorage, tmp_path: Path, filename: str
) -> None:
    (tmp_path.parent / "secret.txt").write_text("tajne", encoding="utf-8")
    with pytest.raises(NotFoundError):
        storage.path_for(filename)


def test_delete_removes_file_and_ignores_missing(storage: PhotoStorage, tmp_path: Path) -> None:
    first = storage.save(1, io.BytesIO(PNG))
    second = storage.save(1, io.BytesIO(JPEG))
    storage.delete_many([first.filename, second.filename, "trip_1/nie-ma.png"])
    assert not (tmp_path / first.filename).exists()
    assert not (tmp_path / second.filename).exists()
