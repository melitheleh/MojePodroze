"""Kosztorys: suma, podział na sekcje, budżet i progi alertu (89/90/100/101%)."""

from decimal import Decimal

import pytest

from app.domain.costs import (
    BudgetAlertLevel,
    budget_alert_level,
    compare_with_budget,
    summarize_costs,
    summarize_section,
    total_cost,
)
from app.domain.enums import PlaceKind, Section, TripType
from app.domain.items import Expense, Flight, Meal, Place, Transport

D = Decimal


@pytest.mark.parametrize(
    ("spent", "expected"),
    [
        (D("0"), BudgetAlertLevel.OK),
        (D("89.99"), BudgetAlertLevel.OK),
        (D("89"), BudgetAlertLevel.OK),
        (D("90"), BudgetAlertLevel.WARNING),
        (D("99.99"), BudgetAlertLevel.WARNING),
        (D("100"), BudgetAlertLevel.WARNING),
        (D("100.01"), BudgetAlertLevel.EXCEEDED),
        (D("101"), BudgetAlertLevel.EXCEEDED),
    ],
)
def test_budget_alert_thresholds(spent: Decimal, expected: BudgetAlertLevel) -> None:
    assert budget_alert_level(spent, D("100")) is expected


def test_no_budget_means_no_alert() -> None:
    assert budget_alert_level(D("1000"), None) is BudgetAlertLevel.NO_BUDGET


def test_budget_comparison_when_money_is_left() -> None:
    result = compare_with_budget(D("750.50"), D("1000"))
    assert result.planned_budget == D("1000")
    assert result.spent == D("750.50")
    assert result.remaining == D("249.50")
    assert result.overrun == D("0")
    assert result.usage_percent == D("75.05")
    assert result.alert_level is BudgetAlertLevel.OK


def test_budget_comparison_when_budget_is_exceeded() -> None:
    result = compare_with_budget(D("1200"), D("1000"))
    assert result.remaining == D("0")
    assert result.overrun == D("200")
    assert result.usage_percent == D("120.00")
    assert result.alert_level is BudgetAlertLevel.EXCEEDED


def test_budget_comparison_when_budget_is_spent_exactly() -> None:
    result = compare_with_budget(D("1000"), D("1000"))
    assert result.remaining == D("0")
    assert result.overrun == D("0")
    assert result.usage_percent == D("100.00")
    assert result.alert_level is BudgetAlertLevel.WARNING


def test_usage_percent_is_rounded_half_up() -> None:
    assert compare_with_budget(D("1"), D("3")).usage_percent == D("33.33")
    assert compare_with_budget(D("2"), D("3")).usage_percent == D("66.67")


def test_budget_comparison_without_budget() -> None:
    result = compare_with_budget(D("300"), None)
    assert result.planned_budget is None
    assert result.spent == D("300")
    assert result.remaining is None
    assert result.overrun is None
    assert result.usage_percent is None
    assert result.alert_level is BudgetAlertLevel.NO_BUDGET


@pytest.mark.parametrize("budget", [D("0"), D("-5")])
def test_non_positive_budget_is_rejected(budget: Decimal) -> None:
    with pytest.raises(ValueError, match="większy od zera"):
        compare_with_budget(D("1"), budget)


def test_total_cost_sums_all_items_exactly() -> None:
    items = [Expense(cost=D("0.10")), Expense(cost=D("0.20")), Expense(cost=D("0.05"))]
    assert total_cost(items) == D("0.35")


def test_total_cost_of_no_items_is_zero() -> None:
    assert total_cost([]) == D("0.00")


def test_section_summary_ignores_missing_ratings() -> None:
    items = [
        Meal(cost=D("40"), rating=5, restaurant_name="A"),
        Meal(cost=D("60"), rating=None, restaurant_name="B"),
        Meal(cost=D("20"), rating=2, restaurant_name="C"),
    ]
    summary = summarize_section(Section.MEALS, items)
    assert summary.section is Section.MEALS
    assert summary.total_cost == D("120.00")
    assert summary.items_count == 3
    assert summary.rated_items_count == 2
    assert summary.average_rating == D("3.50")


def test_empty_section_summary() -> None:
    summary = summarize_section(Section.EXPENSES, [])
    assert summary.total_cost == D("0.00")
    assert summary.items_count == 0
    assert summary.rated_items_count == 0
    assert summary.average_rating is None


def full_trip_items() -> list:
    return [
        Flight(cost=D("1200"), rating=4),
        Flight(cost=D("1100"), rating=2),
        Transport(cost=D("80.50"), rating=5),
        Meal(cost=D("120"), rating=5, restaurant_name="Trattoria"),
        Place(cost=D("900"), rating=4, name="Hotel", kind=PlaceKind.ACCOMMODATION),
        Expense(cost=D("99.50"), category="Pamiątki"),
    ]


def test_cost_summary_of_foreign_trip() -> None:
    summary = summarize_costs(
        full_trip_items(), trip_type=TripType.FOREIGN, planned_budget=D("4000"), trip_days=5
    )
    assert summary.total_cost == D("3500.00")
    assert [section.section for section in summary.sections] == list(Section)
    totals = {section.section: section.total_cost for section in summary.sections}
    assert totals == {
        Section.FLIGHTS: D("2300.00"),
        Section.TRANSPORT: D("80.50"),
        Section.MEALS: D("120.00"),
        Section.PLACES: D("900.00"),
        Section.EXPENSES: D("99.50"),
    }
    # (4 + 2 + 5 + 5 + 4) / 5 = 4.0 — wydatek bez oceny nie wpływa na średnią
    assert summary.average_rating == D("4.00")
    assert summary.rated_items_count == 5
    assert summary.trip_days == 5
    assert summary.average_daily_cost == D("700.00")
    assert summary.budget.remaining == D("500.00")


def test_cost_summary_budget_level_matches_usage() -> None:
    summary = summarize_costs(
        full_trip_items(), trip_type=TripType.FOREIGN, planned_budget=D("4000"), trip_days=5
    )
    assert summary.budget.usage_percent == D("87.50")
    assert summary.budget.alert_level is BudgetAlertLevel.OK


def test_domestic_trip_summary_has_no_flight_section() -> None:
    summary = summarize_costs([], trip_type=TripType.DOMESTIC, planned_budget=None, trip_days=1)
    assert [section.section for section in summary.sections] == [
        Section.TRANSPORT,
        Section.MEALS,
        Section.PLACES,
        Section.EXPENSES,
    ]
    assert summary.total_cost == D("0.00")
    assert summary.average_rating is None
    assert summary.rated_items_count == 0
    assert summary.average_daily_cost == D("0.00")
    assert summary.budget.alert_level is BudgetAlertLevel.NO_BUDGET


def test_disallowed_section_is_still_shown_when_it_has_items() -> None:
    summary = summarize_costs(
        [Flight(cost=D("10"))], trip_type=TripType.DOMESTIC, planned_budget=None, trip_days=1
    )
    assert summary.sections[0].section is Section.FLIGHTS
    assert summary.total_cost == D("10.00")


def test_average_daily_cost_is_rounded() -> None:
    summary = summarize_costs(
        [Expense(cost=D("100"))], trip_type=TripType.DOMESTIC, planned_budget=None, trip_days=3
    )
    assert summary.average_daily_cost == D("33.33")


def test_trip_must_last_at_least_one_day() -> None:
    with pytest.raises(ValueError, match="co najmniej jeden dzień"):
        summarize_costs([], trip_type=TripType.DOMESTIC, planned_budget=None, trip_days=0)
