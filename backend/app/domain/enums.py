"""Wyliczenia domenowe. Wartości (angielskie) idą do API i bazy, etykiety (polskie) do GUI."""

from enum import StrEnum
from typing import Self


class LabeledEnum(StrEnum):
    """StrEnum z dodatkową polską etykietą: ``Member = "value", "etykieta"``."""

    label: str

    def __new__(cls, value: str, label: str) -> Self:
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member


class TripStatus(LabeledEnum):
    PLANNED = "planned", "w planie"
    IN_PROGRESS = "in_progress", "w trakcie"
    COMPLETED = "completed", "zrealizowana"
    ARCHIVED = "archived", "archiwum"


class TripType(LabeledEnum):
    DOMESTIC = "domestic", "krajowa"
    FOREIGN = "foreign", "zagraniczna"


class Section(LabeledEnum):
    """Sekcje pozycji kosztowych podróży (kolejność = kolejność w kosztorysie)."""

    FLIGHTS = "flights", "Loty"
    TRANSPORT = "transport", "Transport"
    MEALS = "meals", "Posiłki"
    PLACES = "places", "Noclegi i atrakcje"
    EXPENSES = "expenses", "Wydatki inne"


class PlaceKind(LabeledEnum):
    ACCOMMODATION = "accommodation", "nocleg"
    ATTRACTION = "attraction", "atrakcja"


class RecommendationCategory(LabeledEnum):
    RESTAURANT = "restaurant", "restauracja"
    ACCOMMODATION = "accommodation", "nocleg"
    ATTRACTION = "attraction", "atrakcja"


class Currency(LabeledEnum):
    """Waluty obsługiwane przez widżet kursów i kalkulator (koszty podróży są tylko w PLN)."""

    EUR = "EUR", "euro"
    USD = "USD", "dolar amerykański"
    GBP = "GBP", "funt szterling"
