"""Odliczanie do najbliższej podróży („zamrożona” data) i statystyki zbiorcze."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import TripStatus, TripType
from app.domain.stats import (
    REALIZED_STATUSES,
    TripCost,
    average_daily_cost,
    build_statistics,
    cost_by_character,
    trips_per_year,
)
from app.domain.trips import TripSnapshot, next_trip_countdown

TODAY = date(2027, 4, 20)


def trip(
    trip_id: int,
    start: date,
    end: date | None = None,
    status: TripStatus = TripStatus.PLANNED,
    character: str = "Góry",
) -> TripSnapshot:
    return TripSnapshot(
        id=trip_id,
        name=f"Podróż {trip_id}",
        destination_city="Zakopane",
        start_date=start,
        end_date=end or start,
        status=status,
        trip_type=TripType.DOMESTIC,
        character=character,
    )


# --- Odliczanie -----------------------------------------------------------------------------


def test_countdown_picks_nearest_planned_trip() -> None:
    trips = [trip(1, date(2027, 6, 1)), trip(2, date(2027, 5, 2)), trip(3, date(2027, 7, 1))]
    countdown = next_trip_countdown(trips, TODAY)
    assert countdown is not None
    assert countdown.trip.id == 2
    assert countdown.days_left == 12


def test_trip_starting_today_has_zero_days_left() -> None:
    countdown = next_trip_countdown([trip(1, TODAY)], TODAY)
    assert countdown is not None
    assert countdown.days_left == 0


def test_trip_starting_tomorrow_has_one_day_left() -> None:
    countdown = next_trip_countdown([trip(1, date(2027, 4, 21))], TODAY)
    assert countdown is not None
    assert countdown.days_left == 1


def test_past_planned_trips_are_ignored() -> None:
    assert next_trip_countdown([trip(1, date(2027, 4, 19))], TODAY) is None


@pytest.mark.parametrize(
    "status", [TripStatus.IN_PROGRESS, TripStatus.COMPLETED, TripStatus.ARCHIVED]
)
def test_only_planned_trips_are_counted_down(status: TripStatus) -> None:
    assert next_trip_countdown([trip(1, date(2027, 5, 1), status=status)], TODAY) is None


def test_same_start_date_prefers_lower_id() -> None:
    countdown = next_trip_countdown([trip(5, date(2027, 5, 1)), trip(3, date(2027, 5, 1))], TODAY)
    assert countdown is not None
    assert countdown.trip.id == 3


def test_no_trips_no_countdown() -> None:
    assert next_trip_countdown([], TODAY) is None


# --- Statystyki -----------------------------------------------------------------------------


def cost(
    trip_id: int,
    total: str,
    *,
    start: date,
    days: int = 1,
    status: TripStatus = TripStatus.COMPLETED,
    character: str = "Góry",
) -> TripCost:
    end = date.fromordinal(start.toordinal() + days - 1)
    return TripCost(trip(trip_id, start, end, status, character), Decimal(total))


def test_realized_statuses() -> None:
    assert frozenset({TripStatus.COMPLETED, TripStatus.ARCHIVED}) == REALIZED_STATUSES


def test_statistics_use_only_completed_and_archived_trips() -> None:
    costs = [
        cost(1, "1000", start=date(2026, 1, 10), days=2),
        cost(2, "500", start=date(2026, 7, 1), days=3, status=TripStatus.ARCHIVED),
        cost(3, "9999", start=date(2026, 8, 1), status=TripStatus.PLANNED),
        cost(4, "9999", start=date(2026, 9, 1), status=TripStatus.IN_PROGRESS),
    ]
    stats = build_statistics(costs)
    assert stats.realized_trips_count == 2
    assert stats.total_cost == Decimal("1500.00")
    assert stats.average_trip_cost == Decimal("750.00")
    assert stats.average_daily_cost == Decimal("300.00")  # 1500 / 5 dni


def test_statistics_without_realized_trips() -> None:
    stats = build_statistics([cost(1, "100", start=date(2026, 1, 1), status=TripStatus.PLANNED)])
    assert stats.realized_trips_count == 0
    assert stats.total_cost == Decimal("0.00")
    assert stats.average_trip_cost is None
    assert stats.average_daily_cost is None
    assert stats.trips_per_year == ()
    assert stats.cost_by_character == ()


def test_trips_per_year_sorted_by_year() -> None:
    costs = [
        cost(1, "1", start=date(2027, 1, 1)),
        cost(2, "1", start=date(2025, 6, 1)),
        cost(3, "1", start=date(2027, 8, 1)),
    ]
    assert [(y.year, y.trips_count) for y in trips_per_year(costs)] == [(2025, 1), (2027, 2)]


def test_cost_by_character_compares_mountains_and_sea() -> None:
    costs = [
        cost(1, "1000", start=date(2026, 1, 1), days=4, character="Góry"),
        cost(2, "2000", start=date(2026, 2, 1), days=4, character="Góry"),
        cost(3, "3000", start=date(2026, 7, 1), days=6, character="Morze"),
    ]
    result = {item.character: item for item in cost_by_character(costs)}
    assert list(result) == ["Góry", "Morze"]
    assert result["Góry"].trips_count == 2
    assert result["Góry"].total_cost == Decimal("3000.00")
    assert result["Góry"].average_cost == Decimal("1500.00")
    assert result["Góry"].average_daily_cost == Decimal("375.00")
    assert result["Morze"].average_daily_cost == Decimal("500.00")


def test_cost_by_character_sorted_alphabetically_ignoring_case() -> None:
    costs = [
        cost(1, "1", start=date(2026, 1, 1), character="morze"),
        cost(2, "1", start=date(2026, 1, 1), character="Góry"),
    ]
    assert [c.character for c in cost_by_character(costs)] == ["Góry", "morze"]


def test_average_daily_cost_of_nothing_is_none() -> None:
    assert average_daily_cost([]) is None


def test_average_daily_cost_rounds() -> None:
    assert average_daily_cost([cost(1, "100", start=date(2026, 1, 1), days=3)]) == Decimal("33.33")
