"""Rekomendacje z własnych danych użytkownika.

Przy podróży do miasta, w którym użytkownik już był, aplikacja podpowiada:
* najlepiej ocenione wcześniej restauracje, noclegi i atrakcje,
* niezaliczone punkty z list „chcę odwiedzić” z wcześniejszych podróży do tego miasta.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.common import normalize_name
from app.domain.enums import RecommendationCategory, TripStatus
from app.domain.items import TripItem
from app.domain.ratings import average_rating
from app.domain.trips import TripSnapshot

DEFAULT_MIN_RATING = Decimal("4")
DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class RatedVisit:
    trip_id: int
    category: RecommendationCategory
    name: str
    rating: int | None


@dataclass(frozen=True)
class Recommendation:
    category: RecommendationCategory
    name: str
    average_rating: Decimal
    ratings_count: int
    trip_ids: tuple[int, ...]


@dataclass(frozen=True)
class WishlistEntry:
    trip_id: int
    name: str
    visited: bool


@dataclass(frozen=True)
class PendingWish:
    name: str
    trip_ids: tuple[int, ...]


def is_previous_visit(candidate: TripSnapshot, current: TripSnapshot) -> bool:
    """Czy ``candidate`` to inna, już rozpoczęta podróż do tego samego miasta."""
    return (
        candidate.id != current.id
        and candidate.status is not TripStatus.PLANNED
        and normalize_name(candidate.destination_city) == normalize_name(current.destination_city)
    )


def visits_from_items(trip_id: int, items: Iterable[TripItem]) -> list[RatedVisit]:
    """Zamienia pozycje podróży na wizyty; o tym, czy pozycja się liczy, decyduje sama pozycja."""
    visits = []
    for item in items:
        category = item.recommendation_category()
        name = item.recommendation_name()
        if category is None or not name:
            continue
        visits.append(RatedVisit(trip_id, category, name, item.get_rating()))
    return visits


def rank_recommendations(
    visits: Iterable[RatedVisit],
    *,
    min_rating: Decimal = DEFAULT_MIN_RATING,
    limit: int | None = DEFAULT_LIMIT,
) -> list[Recommendation]:
    """Grupuje wizyty po (kategoria, nazwa) i sortuje: średnia malejąco, liczba ocen, nazwa."""
    groups: dict[tuple[RecommendationCategory, str], list[RatedVisit]] = {}
    for visit in visits:
        if visit.rating is None:
            continue
        groups.setdefault((visit.category, normalize_name(visit.name)), []).append(visit)

    ranked = []
    for (category, _), group in groups.items():
        score = average_rating(visit.rating for visit in group)
        if score is None or score < min_rating:
            continue
        ranked.append(
            Recommendation(
                category=category,
                name=group[0].name,
                average_rating=score,
                ratings_count=len(group),
                trip_ids=tuple(sorted({visit.trip_id for visit in group})),
            )
        )
    ranked.sort(key=lambda rec: (-rec.average_rating, -rec.ratings_count, normalize_name(rec.name)))
    return ranked if limit is None else ranked[:limit]


def pending_wishes(
    previous_entries: Iterable[WishlistEntry], current_names: Iterable[str] = ()
) -> list[PendingWish]:
    """Niezaliczone punkty z wcześniejszych list.

    Punkt odpada, jeśli został zaliczony w którejkolwiek wcześniejszej podróży albo jest już
    na liście bieżącej podróży.
    """
    entries = list(previous_entries)
    skip = {normalize_name(entry.name) for entry in entries if entry.visited}
    skip |= {normalize_name(name) for name in current_names}

    groups: dict[str, list[WishlistEntry]] = {}
    for entry in entries:
        key = normalize_name(entry.name)
        if key not in skip:
            groups.setdefault(key, []).append(entry)

    wishes = [
        PendingWish(name=group[0].name, trip_ids=tuple(sorted({e.trip_id for e in group})))
        for group in groups.values()
    ]
    return sorted(wishes, key=lambda wish: normalize_name(wish.name))
