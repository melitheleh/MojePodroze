"""Ranking rekomendacji i przypomnienia z list „chcę odwiedzić”."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import PlaceKind, RecommendationCategory, TripStatus, TripType
from app.domain.items import Expense, Flight, Meal, Place, Transport
from app.domain.recommendations import (
    PendingWish,
    RatedVisit,
    WishlistEntry,
    is_previous_visit,
    pending_wishes,
    rank_recommendations,
    visits_from_items,
)
from app.domain.trips import TripSnapshot

RESTAURANT = RecommendationCategory.RESTAURANT
ATTRACTION = RecommendationCategory.ATTRACTION


def snapshot(
    trip_id: int, city: str = "Kraków", status: TripStatus = TripStatus.COMPLETED
) -> TripSnapshot:
    return TripSnapshot(
        id=trip_id,
        name=f"Podróż {trip_id}",
        destination_city=city,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 3),
        status=status,
        trip_type=TripType.DOMESTIC,
        character="Miasto",
    )


def visit(name: str, rating: int | None, trip_id: int = 1, category=RESTAURANT) -> RatedVisit:
    return RatedVisit(trip_id=trip_id, category=category, name=name, rating=rating)


# --- Które podróże są „wcześniejsze” -------------------------------------------------------


@pytest.mark.parametrize(
    "status", [TripStatus.IN_PROGRESS, TripStatus.COMPLETED, TripStatus.ARCHIVED]
)
def test_started_trip_to_same_city_counts(status: TripStatus) -> None:
    assert is_previous_visit(snapshot(1, status=status), snapshot(2))


def test_city_comparison_ignores_case_and_spaces() -> None:
    assert is_previous_visit(snapshot(1, city="  KRAKÓW "), snapshot(2, city="kraków"))


def test_same_trip_is_not_previous_visit() -> None:
    assert not is_previous_visit(snapshot(2), snapshot(2))


def test_planned_trip_is_not_previous_visit() -> None:
    assert not is_previous_visit(snapshot(1, status=TripStatus.PLANNED), snapshot(2))


def test_other_city_is_not_previous_visit() -> None:
    assert not is_previous_visit(snapshot(1, city="Gdańsk"), snapshot(2))


# --- Zamiana pozycji na wizyty (polimorfizm) -----------------------------------------------


def test_only_meals_and_places_become_visits() -> None:
    items = [
        Flight(cost=Decimal("1"), rating=5),
        Transport(cost=Decimal("1"), rating=5),
        Expense(cost=Decimal("1")),
        Meal(cost=Decimal("1"), rating=4, restaurant_name="Bar"),
        Place(cost=Decimal("1"), rating=3, name="Wawel"),
        Place(cost=Decimal("1"), rating=5, name="Hotel", kind=PlaceKind.ACCOMMODATION),
    ]
    assert visits_from_items(7, items) == [
        RatedVisit(7, RESTAURANT, "Bar", 4),
        RatedVisit(7, ATTRACTION, "Wawel", 3),
        RatedVisit(7, RecommendationCategory.ACCOMMODATION, "Hotel", 5),
    ]


def test_items_with_empty_name_are_skipped() -> None:
    assert visits_from_items(1, [Meal(cost=Decimal("1"), rating=5, restaurant_name="")]) == []


# --- Ranking --------------------------------------------------------------------------------


def test_ranking_sorts_by_average_rating_descending() -> None:
    ranked = rank_recommendations([visit("B", 4), visit("A", 5), visit("C", 4, trip_id=2)])
    assert [r.name for r in ranked] == ["A", "B", "C"]


def test_ties_are_broken_by_number_of_ratings_then_name() -> None:
    visits = [visit("Zorba", 5), visit("Zorba", 5, trip_id=2), visit("Alfa", 5), visit("Beta", 5)]
    ranked = rank_recommendations(visits)
    assert [r.name for r in ranked] == ["Zorba", "Alfa", "Beta"]
    assert ranked[0].ratings_count == 2
    assert ranked[0].trip_ids == (1, 2)


def test_same_place_is_grouped_ignoring_case_and_averaged() -> None:
    ranked = rank_recommendations([visit("Pod Aniołami", 5), visit("pod aniołami ", 4, 3)])
    assert len(ranked) == 1
    assert ranked[0].name == "Pod Aniołami"
    assert ranked[0].average_rating == Decimal("4.50")
    assert ranked[0].trip_ids == (1, 3)


def test_same_name_in_different_categories_is_not_merged() -> None:
    ranked = rank_recommendations([visit("Wawel", 5), visit("Wawel", 5, category=ATTRACTION)])
    assert {r.category for r in ranked} == {RESTAURANT, ATTRACTION}


@pytest.mark.parametrize(
    ("ratings", "included"),
    [((4,), True), ((5, 3), True), ((4, 3), False), ((3,), False)],
)
def test_minimum_rating_threshold_is_inclusive(ratings: tuple[int, ...], included: bool) -> None:
    ranked = rank_recommendations([visit("X", r, trip_id=i) for i, r in enumerate(ratings)])
    assert bool(ranked) is included


def test_custom_minimum_rating() -> None:
    assert rank_recommendations([visit("X", 3)], min_rating=Decimal("3"))
    assert not rank_recommendations([visit("X", 3)], min_rating=Decimal("3.5"))


def test_unrated_visits_are_ignored() -> None:
    assert rank_recommendations([visit("X", None)]) == []


def test_limit_cuts_the_list() -> None:
    visits = [visit(f"Miejsce {i}", 5) for i in range(10)]
    assert len(rank_recommendations(visits)) == 5
    assert len(rank_recommendations(visits, limit=2)) == 2
    assert len(rank_recommendations(visits, limit=None)) == 10


# --- Lista „chcę odwiedzić” -----------------------------------------------------------------


def test_pending_wishes_skip_visited_and_group_by_name() -> None:
    entries = [
        WishlistEntry(1, "Kopiec Kościuszki", visited=False),
        WishlistEntry(2, "kopiec kościuszki", visited=False),
        WishlistEntry(1, "Wawel", visited=True),
        WishlistEntry(2, "Kazimierz", visited=False),
    ]
    assert pending_wishes(entries) == [
        PendingWish("Kazimierz", (2,)),
        PendingWish("Kopiec Kościuszki", (1, 2)),
    ]


def test_wish_visited_on_any_previous_trip_is_skipped() -> None:
    entries = [WishlistEntry(1, "Wawel", visited=False), WishlistEntry(2, "WAWEL", visited=True)]
    assert pending_wishes(entries) == []


def test_wish_already_on_current_list_is_skipped() -> None:
    entries = [WishlistEntry(1, "Wawel", visited=False), WishlistEntry(1, "Sukiennice", False)]
    assert pending_wishes(entries, current_names=[" wawel"]) == [PendingWish("Sukiennice", (1,))]


def test_no_previous_entries_means_no_wishes() -> None:
    assert pending_wishes([]) == []
