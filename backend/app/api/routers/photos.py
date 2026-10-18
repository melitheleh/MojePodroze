from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DbSession, OwnedTrip, Storage, Today
from app.api.responses import READ, WRITE
from app.schemas.common import ErrorResponse
from app.schemas.photos import AlbumDayOut, PhotoOut, PhotoPatch
from app.services import photos as photos_service

router = APIRouter(prefix="/trips/{trip_id}", tags=["Zdjęcia i album"])

PhotoId = Annotated[int, Path(ge=1, description="Id zdjęcia.")]


@router.get("/photos", summary="Lista zdjęć", responses=READ, name="list_photos")
def list_photos(trip: OwnedTrip, db: DbSession) -> list[PhotoOut]:
    return [PhotoOut.model_validate(photo) for photo in photos_service.list_photos(db, trip)]


@router.post(
    "/photos",
    status_code=status.HTTP_201_CREATED,
    summary="Wgraj zdjęcie",
    description=(
        "Formularz multipart: `file` (JPG, PNG, GIF lub WEBP, domyślnie maks. 10 MB), "
        "opcjonalnie `day` (dzień albumu; domyślnie dzisiejsza data) i `caption`. "
        "Format jest sprawdzany po zawartości pliku. Archiwum → 409."
    ),
    responses={**WRITE, 413: {"model": ErrorResponse, "description": "Plik za duży."}},
    name="upload_photo",
)
def upload_photo(
    trip: OwnedTrip,
    db: DbSession,
    storage: Storage,
    today: Today,
    file: Annotated[UploadFile, File(description="Plik zdjęcia.")],
    day: Annotated[date | None, Form(description="Dzień albumu (RRRR-MM-DD).")] = None,
    caption: Annotated[str | None, Form(max_length=255)] = None,
) -> PhotoOut:
    photo = photos_service.upload_photo(
        db,
        storage,
        trip,
        source=file.file,
        original_filename=file.filename,
        day=day or today,
        caption=caption.strip() if caption and caption.strip() else None,
    )
    return PhotoOut.model_validate(photo)


@router.get("/photos/{photo_id}", summary="Metadane zdjęcia", responses=READ, name="get_photo")
def get_photo(trip: OwnedTrip, db: DbSession, photo_id: PhotoId) -> PhotoOut:
    return PhotoOut.model_validate(photos_service.get_photo(db, trip, photo_id))


@router.patch(
    "/photos/{photo_id}",
    summary="Zmień dzień lub podpis zdjęcia",
    responses=WRITE,
    name="update_photo",
)
def update_photo(
    trip: OwnedTrip, db: DbSession, photo_id: PhotoId, payload: PhotoPatch
) -> PhotoOut:
    changes = payload.model_dump(exclude_unset=True)
    return PhotoOut.model_validate(photos_service.update_photo(db, trip, photo_id, changes))


@router.delete(
    "/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Usuń zdjęcie",
    responses=WRITE,
    name="delete_photo",
)
def delete_photo(trip: OwnedTrip, db: DbSession, storage: Storage, photo_id: PhotoId) -> None:
    photos_service.delete_photo(db, storage, trip, photo_id)


@router.get(
    "/photos/{photo_id}/file",
    response_class=FileResponse,
    summary="Plik zdjęcia",
    description=(
        "Zwraca obraz. Wymaga nagłówka X-User-Id, dlatego GUI pobiera go przez fetch "
        "i wyświetla jako `URL.createObjectURL(blob)`."
    ),
    responses={**READ, 200: {"content": {"image/*": {}}, "description": "Plik obrazu."}},
    name="get_photo_file",
)
def get_photo_file(
    trip: OwnedTrip, db: DbSession, storage: Storage, photo_id: PhotoId
) -> FileResponse:
    path, photo = photos_service.photo_file_path(db, storage, trip, photo_id)
    return FileResponse(path, media_type=photo.content_type)


@router.get(
    "/album",
    summary="Album według dni",
    description="Zdjęcia pogrupowane po dniach (rosnąco). Dostępne także w archiwum.",
    responses=READ,
    name="get_album",
)
def get_album(trip: OwnedTrip, db: DbSession) -> list[AlbumDayOut]:
    return [
        AlbumDayOut(day=day, photos=[PhotoOut.model_validate(photo) for photo in photos])
        for day, photos in photos_service.album(db, trip)
    ]
