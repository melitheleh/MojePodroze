"""Polimorficzne pozycje podróży i reguły sekcji zależne od typu podróży."""

from decimal import Decimal

import pytest

from app.domain.enums import PlaceKind, RecommendationCategory, Section, TripType
from app.domain.errors import SectionNotAllowedError
from app.domain.items import (
    ITEM_CLASSES,
    Expense,
    Flight,
    Meal,
    Place,
    Transport,
    TripItem,
    allowed_sections,
    ensure_section_allowed,
    is_section_allowed,
)

DOMESTIC = TripType.DOMESTIC
FOREIGN = TripType.FOREIGN


def sample_items() -> list[TripItem]:
    return [
        Flight(cost=Decimal("800"), rating=4, flight_number="LO1"),
        Transport(cost=Decimal("50"), rating=3, means="Pociąg"),
        Meal(cost=Decimal("90"), rating=5, restaurant_name="Trattoria"),
        Place(cost=Decimal("300"), rating=2, name="Hotel", kind=PlaceKind.ACCOMMODATION),
        Expense(cost=Decimal("25"), category="Pamiątki"),
    ]


def test_every_section_has_exactly_one_item_class() -> None:
    assert set(ITEM_CLASSES) == set(Section)
    for section, item_class in ITEM_CLASSES.items():
        assert item_class.section is section


def test_polymorphic_interface_returns_cost_section_and_rating() -> None:
    items = sample_items()
    assert [item.get_section() for item in items] == list(Section)
    assert [item.get_cost() for item in items] == [
        Decimal("800"),
        Decimal("50"),
        Decimal("90"),
        Decimal("300"),
        Decimal("25"),
    ]
    assert [item.get_rating() for item in items] == [4, 3, 5, 2, None]


def test_expense_has_no_rating() -> None:
    assert Expense(cost=Decimal("10")).get_rating() is None


def test_rating_is_optional_for_rated_items() -> None:
    assert Meal(cost=Decimal("10"), restaurant_name="Bar").get_rating() is None


@pytest.mark.parametrize("rating", [1, 5])
def test_rating_accepts_boundaries(rating: int) -> None:
    assert Transport(cost=Decimal("1"), rating=rating).get_rating() == rating


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_rating_outside_scale_is_rejected(rating: int) -> None:
    with pytest.raises(ValueError, match="1–5"):
        Transport(cost=Decimal("1"), rating=rating)


def test_zero_cost_is_allowed() -> None:
    assert Expense(cost=Decimal("0")).get_cost() == Decimal("0")


def test_negative_cost_is_rejected() -> None:
    with pytest.raises(ValueError, match="ujemny"):
        Expense(cost=Decimal("-0.01"))


def test_negative_cost_is_rejected_for_rated_items() -> None:
    with pytest.raises(ValueError, match="ujemny"):
        Meal(cost=Decimal("-1"), restaurant_name="Bar", rating=3)


@pytest.mark.parametrize(
    ("item_class", "domestic", "foreign"),
    [
        (Flight, False, True),
        (Transport, True, True),
        (Meal, True, True),
        (Place, True, True),
        (Expense, True, True),
    ],
)
def test_item_availability_depends_on_trip_type(
    item_class: type[TripItem], domestic: bool, foreign: bool
) -> None:
    assert item_class.is_allowed_for(DOMESTIC) is domestic
    assert item_class.is_allowed_for(FOREIGN) is foreign


def test_allowed_sections_for_domestic_trip_exclude_flights() -> None:
    assert allowed_sections(DOMESTIC) == (
        Section.TRANSPORT,
        Section.MEALS,
        Section.PLACES,
        Section.EXPENSES,
    )


def test_foreign_trip_allows_every_section() -> None:
    assert allowed_sections(FOREIGN) == tuple(Section)
    assert all(is_section_allowed(section, FOREIGN) for section in Section)


def test_adding_flight_to_domestic_trip_raises_error() -> None:
    with pytest.raises(SectionNotAllowedError) as error:
        ensure_section_allowed(Section.FLIGHTS, DOMESTIC)
    assert error.value.code == "SECTION_NOT_ALLOWED"
    assert "Loty" in error.value.message
    assert "krajowa" in error.value.message


def test_allowed_section_does_not_raise() -> None:
    ensure_section_allowed(Section.FLIGHTS, FOREIGN)
    ensure_section_allowed(Section.MEALS, DOMESTIC)


def test_meal_is_recommended_as_restaurant() -> None:
    meal = Meal(cost=Decimal("40"), restaurant_name="Pod Aniołami", dish="Żurek")
    assert meal.recommendation_category() is RecommendationCategory.RESTAURANT
    assert meal.recommendation_name() == "Pod Aniołami"


@pytest.mark.parametrize(
    ("kind", "category"),
    [
        (PlaceKind.ACCOMMODATION, RecommendationCategory.ACCOMMODATION),
        (PlaceKind.ATTRACTION, RecommendationCategory.ATTRACTION),
    ],
)
def test_place_category_follows_its_kind(kind: PlaceKind, category: RecommendationCategory) -> None:
    place = Place(cost=Decimal("0"), name="Wawel", kind=kind)
    assert place.recommendation_category() is category
    assert place.recommendation_name() == "Wawel"


def test_place_is_attraction_by_default() -> None:
    assert Place(cost=Decimal("0"), name="Rynek").kind is PlaceKind.ATTRACTION


@pytest.mark.parametrize(
    "item",
    [
        Flight(cost=Decimal("1")),
        Transport(cost=Decimal("1")),
        Expense(cost=Decimal("1")),
    ],
)
def test_other_items_are_not_recommended(item: TripItem) -> None:
    assert item.recommendation_category() is None
    assert item.recommendation_name() is None
