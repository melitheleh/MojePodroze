"""Zapis plików zdjęć na dysku. Baza przechowuje tylko ścieżkę względną (``stored_filename``)."""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.errors import FileTooLargeError, InvalidUploadError, NotFoundError

MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}
HEADER_SIZE = 12


def detect_image_type(header: bytes) -> str | None:
    """Rozpoznaje format po „magicznych bajtach”, a nie po rozszerzeniu podanym przez klienta."""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


@dataclass(frozen=True)
class StoredFile:
    filename: str  # ścieżka względna, np. "trip_7/3f2c...e1.jpg"
    media_type: str
    size_bytes: int


class PhotoStorage:
    def __init__(self, base_dir: Path, max_bytes: int) -> None:
        self._base_dir = base_dir
        self._max_bytes = max_bytes

    def save(self, trip_id: int, source: BinaryIO) -> StoredFile:
        data = source.read(self._max_bytes + 1)
        if len(data) > self._max_bytes:
            max_mb = self._max_bytes / (1024 * 1024)
            raise FileTooLargeError(f"Plik jest za duży. Maksymalny rozmiar to {max_mb:g} MB.")
        if not data:
            raise InvalidUploadError("Plik jest pusty.")
        extension = detect_image_type(data[:HEADER_SIZE])
        if extension is None:
            raise InvalidUploadError("Dozwolone są tylko zdjęcia JPG, PNG, GIF lub WEBP.")

        filename = f"trip_{trip_id}/{uuid.uuid4().hex}.{extension}"
        path = self._base_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredFile(filename, MEDIA_TYPES[extension], len(data))

    def path_for(self, filename: str) -> Path:
        """Pełna ścieżka pliku; chroni przed wyjściem poza katalog zdjęć (path traversal)."""
        base = self._base_dir.resolve()
        path = (base / filename).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise NotFoundError("Nie znaleziono pliku zdjęcia.")
        return path

    def delete(self, filename: str) -> None:
        try:
            self.path_for(filename).unlink(missing_ok=True)
        except NotFoundError:
            return

    def delete_many(self, filenames: Iterable[str]) -> None:
        for filename in filenames:
            self.delete(filename)
