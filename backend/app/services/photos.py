from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import Photo, Trip
from app.domain.album import group_by_day
from app.domain.status import ensure_editable
from app.services.photo_storage import PhotoStorage

DEFAULT_FILENAME = "zdjecie"


def list_photos(db: Session, trip: Trip) -> Sequence[Photo]:
    return db.scalars(
        select(Photo)
        .where(Photo.trip_id == trip.id)
        .order_by(Photo.day, Photo.uploaded_at, Photo.id)
    ).all()


def album(db: Session, trip: Trip) -> list[tuple[date, list[Photo]]]:
    return group_by_day(list_photos(db, trip), lambda photo: photo.day)


def get_photo(db: Session, trip: Trip, photo_id: int) -> Photo:
    photo = db.scalar(select(Photo).where(Photo.id == photo_id, Photo.trip_id == trip.id))
    if photo is None:
        raise NotFoundError("Nie znaleziono zdjęcia.")
    return photo


def upload_photo(
    db: Session,
    storage: PhotoStorage,
    trip: Trip,
    *,
    source: BinaryIO,
    original_filename: str | None,
    day: date,
    caption: str | None,
) -> Photo:
    """Zapisuje plik na dysku i metadane w bazie. Dzień domyślnie = data dodania."""
    ensure_editable(trip.status)
    stored = storage.save(trip.id, source)
    photo = Photo(
        trip_id=trip.id,
        original_filename=(original_filename or DEFAULT_FILENAME)[:255],
        stored_filename=stored.filename,
        content_type=stored.media_type,
        size_bytes=stored.size_bytes,
        day=day,
        caption=caption,
    )
    db.add(photo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(stored.filename)  # nie zostawiaj osieroconego pliku
        raise
    db.refresh(photo)
    return photo


def update_photo(db: Session, trip: Trip, photo_id: int, changes: dict[str, object]) -> Photo:
    ensure_editable(trip.status)
    photo = get_photo(db, trip, photo_id)
    for field, value in changes.items():
        setattr(photo, field, value)
    db.commit()
    db.refresh(photo)
    return photo


def delete_photo(db: Session, storage: PhotoStorage, trip: Trip, photo_id: int) -> None:
    ensure_editable(trip.status)
    photo = get_photo(db, trip, photo_id)
    filename = photo.stored_filename
    db.delete(photo)
    db.commit()
    storage.delete(filename)


def photo_file_path(
    db: Session, storage: PhotoStorage, trip: Trip, photo_id: int
) -> tuple[Path, Photo]:
    photo = get_photo(db, trip, photo_id)
    return storage.path_for(photo.stored_filename), photo
