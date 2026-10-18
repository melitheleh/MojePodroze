from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, computed_field

from app.schemas.common import ApiModel, LongName, reject_null


class PhotoPatch(BaseModel):
    day: Annotated[date | None, AfterValidator(reject_null)] = Field(
        default=None, description="Dzień albumu, do którego należy zdjęcie."
    )
    caption: LongName | None = None


class PhotoOut(ApiModel):
    id: int
    trip_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    day: date
    caption: str | None
    uploaded_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_url(self) -> str:
        """Adres pliku. Wymaga nagłówka X-User-Id, więc GUI pobiera go przez fetch → blob."""
        return f"/api/trips/{self.trip_id}/photos/{self.id}/file"


class AlbumDayOut(BaseModel):
    day: date
    photos: list[PhotoOut]
