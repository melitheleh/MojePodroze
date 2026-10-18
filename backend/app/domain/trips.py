"""Lekki, niezależny od bazy obraz podróży oraz odliczanie do najbliższego wyjazdu."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.domain.common import trip_length_days
from app.domain.enums import TripStatus, TripType


@dataclass(frozen=True)
class TripSnapshot:
    id: int
    name: str
    destination_city: str
    start_date: date
    end_date: date
    status: TripStatus
    trip_type: TripType
    character: str

    @property
    def length_days(self) -> int:
        return trip_length_days(self.start_date, self.end_date)


@dataclass(frozen=True)
class Countdown:
    trip: TripSnapshot
    days_left: int


def next_trip_countdown(trips: Iterable[TripSnapshot], today: date) -> Countdown | None:
    """Najbliższa podróż „w planie”, która zaczyna się dziś lub później."""
    upcoming = [
        trip for trip in trips if trip.status is TripStatus.PLANNED and trip.start_date >= today
    ]
    if not upcoming:
        return None
    nearest = min(upcoming, key=lambda trip: (trip.start_date, trip.id))
    return Countdown(trip=nearest, days_left=(nearest.start_date - today).days)
