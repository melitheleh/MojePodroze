from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.dictionaries import DictionariesOut
from app.services.dictionaries import all_dictionaries

router = APIRouter(prefix="/dictionaries", tags=["Słowniki"])


@router.get(
    "",
    summary="Listy wyboru do formularzy",
    description=(
        "Charaktery podróży, środki transportu, kategorie wydatków (z bazy) oraz wartości "
        "wyliczeń z polskimi etykietami: statusy, typy podróży, rodzaje miejsc, sekcje, waluty. "
        "Nie wymaga logowania."
    ),
    name="get_dictionaries",
)
def get_dictionaries(db: DbSession) -> DictionariesOut:
    return all_dictionaries(db)
