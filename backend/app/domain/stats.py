"""Statystyki zbiorcze liczone z podróży zrealizowanych (status „zrealizowana” lub „archiwum”)."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.common import ZERO, normalize_name, round_half_up
from app.domain.enums import TripStatus
from app.domain.trips import TripSnapshot

REALIZED_STATUSES = frozenset({TripStatus.COMPLETED, TripStatus.ARCHIVED})


@dataclass(frozen=True)
class TripCost:
    trip: TripSnapshot
    total_cost: Decimal


@dataclass(frozen=True)
class YearCount:
    year: int
    trips_count: int


@dataclass(frozen=True)
class CharacterCost:
    character: str
    trips_count: int
    total_cost: Decimal
    average_cost: Decimal
    average_daily_cost: Decimal


@dataclass(frozen=True)
class TravelStatistics:
    realized_trips_count: int
    total_cost: Decimal
    average_trip_cost: Decimal | None
    average_daily_cost: Decimal | None
    trips_per_year: tuple[YearCount, ...]
    cost_by_character: tuple[CharacterCost, ...]


def realized_only(trip_costs: Iterable[TripCost]) -> list[TripCost]:
    return [cost for cost in trip_costs if cost.trip.status in REALIZED_STATUSES]


def sum_costs(trip_costs: Sequence[TripCost]) -> Decimal:
    return sum((cost.total_cost for cost in trip_costs), ZERO)


def average_daily_cost(trip_costs: Sequence[TripCost]) -> Decimal | None:
    """Średni koszt dnia = suma kosztów / suma dni wszystkich podróży."""
    days = sum(cost.trip.length_days for cost in trip_costs)
    if days == 0:
        return None
    return round_half_up(sum_costs(trip_costs) / Decimal(days))


def trips_per_year(trip_costs: Iterable[TripCost]) -> tuple[YearCount, ...]:
    counts: dict[int, int] = defaultdict(int)
    for cost in trip_costs:
        counts[cost.trip.start_date.year] += 1
    return tuple(YearCount(year, counts[year]) for year in sorted(counts))


def cost_by_character(trip_costs: Iterable[TripCost]) -> tuple[CharacterCost, ...]:
    groups: dict[str, list[TripCost]] = defaultdict(list)
    for cost in trip_costs:
        groups[cost.trip.character].append(cost)
    result = []
    for character, group in groups.items():
        total = sum_costs(group)
        result.append(
            CharacterCost(
                character=character,
                trips_count=len(group),
                total_cost=round_half_up(total),
                average_cost=round_half_up(total / Decimal(len(group))),
                average_daily_cost=average_daily_cost(group) or ZERO,
            )
        )
    return tuple(sorted(result, key=lambda item: normalize_name(item.character)))


def build_statistics(trip_costs: Iterable[TripCost]) -> TravelStatistics:
    realized = realized_only(trip_costs)
    total = round_half_up(sum_costs(realized))
    return TravelStatistics(
        realized_trips_count=len(realized),
        total_cost=total,
        average_trip_cost=round_half_up(total / Decimal(len(realized))) if realized else None,
        average_daily_cost=average_daily_cost(realized),
        trips_per_year=trips_per_year(realized),
        cost_by_character=cost_by_character(realized),
    )
