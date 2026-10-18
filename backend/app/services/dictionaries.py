from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidReferenceError
from app.db.models import DictionaryMixin, ExpenseCategory, TransportMean, TripCharacter
from app.domain.enums import Currency, LabeledEnum, PlaceKind, Section, TripStatus, TripType
from app.schemas.common import EnumOption
from app.schemas.dictionaries import DictionariesOut, DictionaryEntryOut


def list_entries[T: DictionaryMixin](db: Session, model: type[T]) -> Sequence[T]:
    return db.scalars(select(model).order_by(model.sort_order, model.id)).all()


def ensure_entry_exists(
    db: Session, model: type[DictionaryMixin], entry_id: int, message: str
) -> None:
    if db.get(model, entry_id) is None:
        raise InvalidReferenceError(message)


def enum_options(enum_cls: type[LabeledEnum]) -> list[EnumOption]:
    return [EnumOption(value=member.value, label=member.label) for member in enum_cls]


def _entries(db: Session, model: type[DictionaryMixin]) -> list[DictionaryEntryOut]:
    return [DictionaryEntryOut.model_validate(entry) for entry in list_entries(db, model)]


def all_dictionaries(db: Session) -> DictionariesOut:
    return DictionariesOut(
        trip_characters=_entries(db, TripCharacter),
        transport_means=_entries(db, TransportMean),
        expense_categories=_entries(db, ExpenseCategory),
        trip_statuses=enum_options(TripStatus),
        trip_types=enum_options(TripType),
        place_kinds=enum_options(PlaceKind),
        sections=enum_options(Section),
        currencies=enum_options(Currency),
    )
