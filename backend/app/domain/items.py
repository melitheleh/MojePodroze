"""Pozycje podróży: hierarchia klas z polimorfizmem.

Każda pozycja ma koszt w PLN i (opcjonalnie) jedną ocenę 1–5. Kosztorys, średnie ocen
i rekomendacje korzystają wyłącznie z metod klasy bazowej ``TripItem``, więc nowy rodzaj
pozycji dodaje się jako nową klasę pochodną, bez zmiany kodu kosztorysu.

Odpowiedniki z dokumentu analizy: ``Pozycja`` → ``TripItem``, ``koszt()`` → ``get_cost()``,
``oceny()`` → ``get_rating()``, ``sekcja()`` → ``get_section()``,
``czy_dozwolona_dla(typ)`` → ``is_allowed_for(trip_type)``.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import ClassVar

from app.domain.common import ZERO
from app.domain.enums import PlaceKind, RecommendationCategory, Section, TripType
from app.domain.errors import SectionNotAllowedError

MIN_RATING = 1
MAX_RATING = 5


@dataclass(frozen=True, kw_only=True)
class TripItem(ABC):
    """Klasa bazowa każdej pozycji kosztowej podróży."""

    section: ClassVar[Section]

    cost: Decimal

    def __post_init__(self) -> None:
        if self.cost < ZERO:
            raise ValueError("Koszt nie może być ujemny.")

    def get_cost(self) -> Decimal:
        return self.cost

    def get_section(self) -> Section:
        return self.section

    @abstractmethod
    def get_rating(self) -> int | None:
        """Ocena 1–5 albo ``None``, gdy pozycja nie ma (jeszcze) oceny."""

    @classmethod
    def is_allowed_for(cls, trip_type: TripType) -> bool:
        """Czy pozycje tego rodzaju można dodawać do podróży danego typu."""
        return True

    def recommendation_category(self) -> RecommendationCategory | None:
        """Kategoria w rekomendacjach albo ``None``, gdy pozycja nie trafia do rekomendacji."""
        return None

    def recommendation_name(self) -> str | None:
        return None


@dataclass(frozen=True, kw_only=True)
class RatedTripItem(TripItem, ABC):
    """Pozycja, którą użytkownik może ocenić w skali 1–5."""

    rating: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.rating is not None and not MIN_RATING <= self.rating <= MAX_RATING:
            raise ValueError(f"Ocena musi być w zakresie {MIN_RATING}–{MAX_RATING}.")

    def get_rating(self) -> int | None:
        return self.rating


@dataclass(frozen=True, kw_only=True)
class Flight(RatedTripItem):
    section: ClassVar[Section] = Section.FLIGHTS

    flight_number: str = ""

    @classmethod
    def is_allowed_for(cls, trip_type: TripType) -> bool:
        return trip_type is TripType.FOREIGN


@dataclass(frozen=True, kw_only=True)
class Transport(RatedTripItem):
    section: ClassVar[Section] = Section.TRANSPORT

    means: str = ""
    route: str = ""


@dataclass(frozen=True, kw_only=True)
class Meal(RatedTripItem):
    """Posiłek ma jedną ocenę: ocenę restauracji."""

    section: ClassVar[Section] = Section.MEALS

    restaurant_name: str
    dish: str = ""

    def recommendation_category(self) -> RecommendationCategory | None:
        return RecommendationCategory.RESTAURANT

    def recommendation_name(self) -> str | None:
        return self.restaurant_name


_PLACE_CATEGORIES: Mapping[PlaceKind, RecommendationCategory] = MappingProxyType(
    {
        PlaceKind.ACCOMMODATION: RecommendationCategory.ACCOMMODATION,
        PlaceKind.ATTRACTION: RecommendationCategory.ATTRACTION,
    }
)


@dataclass(frozen=True, kw_only=True)
class Place(RatedTripItem):
    """Nocleg albo atrakcja."""

    section: ClassVar[Section] = Section.PLACES

    name: str
    kind: PlaceKind = PlaceKind.ATTRACTION

    def recommendation_category(self) -> RecommendationCategory | None:
        return _PLACE_CATEGORIES[self.kind]

    def recommendation_name(self) -> str | None:
        return self.name


@dataclass(frozen=True, kw_only=True)
class Expense(TripItem):
    """Wydatek inny: ma kategorię i kwotę, ale nie ma oceny."""

    section: ClassVar[Section] = Section.EXPENSES

    category: str = ""
    description: str = ""

    def get_rating(self) -> int | None:
        return None


ITEM_CLASSES: Mapping[Section, type[TripItem]] = MappingProxyType(
    {cls.section: cls for cls in (Flight, Transport, Meal, Place, Expense)}
)


def is_section_allowed(section: Section, trip_type: TripType) -> bool:
    return ITEM_CLASSES[section].is_allowed_for(trip_type)


def allowed_sections(trip_type: TripType) -> tuple[Section, ...]:
    return tuple(section for section in Section if is_section_allowed(section, trip_type))


def ensure_section_allowed(section: Section, trip_type: TripType) -> None:
    if not is_section_allowed(section, trip_type):
        raise SectionNotAllowedError(
            f"Sekcja „{section.label}” nie jest dostępna dla podróży typu „{trip_type.label}”."
        )
