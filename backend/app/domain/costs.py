"""Kosztorys podróży: suma, podział na sekcje, porównanie z budżetem i alert budżetu."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.common import ZERO, round_half_up
from app.domain.enums import Section, TripType
from app.domain.items import TripItem, is_section_allowed
from app.domain.ratings import average_rating

BUDGET_WARNING_RATIO = Decimal("0.9")
HUNDRED = Decimal("100")


class BudgetAlertLevel(StrEnum):
    NO_BUDGET = "no_budget"
    OK = "ok"
    WARNING = "warning"  # wydano co najmniej 90% budżetu
    EXCEEDED = "exceeded"  # wydano więcej niż budżet


@dataclass(frozen=True)
class BudgetComparison:
    planned_budget: Decimal | None
    spent: Decimal
    remaining: Decimal | None
    overrun: Decimal | None
    usage_percent: Decimal | None
    alert_level: BudgetAlertLevel


@dataclass(frozen=True)
class SectionSummary:
    section: Section
    total_cost: Decimal
    items_count: int
    average_rating: Decimal | None
    rated_items_count: int


@dataclass(frozen=True)
class CostSummary:
    total_cost: Decimal
    sections: tuple[SectionSummary, ...]
    average_rating: Decimal | None
    rated_items_count: int
    budget: BudgetComparison
    trip_days: int
    average_daily_cost: Decimal


def budget_alert_level(spent: Decimal, planned_budget: Decimal | None) -> BudgetAlertLevel:
    """Progi: <90% → ok, 90–100% → ostrzeżenie, >100% → przekroczony."""
    if planned_budget is None:
        return BudgetAlertLevel.NO_BUDGET
    if spent > planned_budget:
        return BudgetAlertLevel.EXCEEDED
    if spent >= planned_budget * BUDGET_WARNING_RATIO:
        return BudgetAlertLevel.WARNING
    return BudgetAlertLevel.OK


def compare_with_budget(spent: Decimal, planned_budget: Decimal | None) -> BudgetComparison:
    level = budget_alert_level(spent, planned_budget)
    if planned_budget is None:
        return BudgetComparison(None, spent, None, None, None, level)
    if planned_budget <= ZERO:
        raise ValueError("Planowany budżet musi być większy od zera.")
    difference = planned_budget - spent
    return BudgetComparison(
        planned_budget=planned_budget,
        spent=spent,
        remaining=difference if difference > ZERO else ZERO,
        overrun=-difference if difference < ZERO else ZERO,
        usage_percent=round_half_up(spent / planned_budget * HUNDRED),
        alert_level=level,
    )


def total_cost(items: Sequence[TripItem]) -> Decimal:
    return round_half_up(sum((item.get_cost() for item in items), ZERO))


def summarize_section(section: Section, items: Sequence[TripItem]) -> SectionSummary:
    ratings = [item.get_rating() for item in items]
    return SectionSummary(
        section=section,
        total_cost=total_cost(items),
        items_count=len(items),
        average_rating=average_rating(ratings),
        rated_items_count=sum(1 for rating in ratings if rating is not None),
    )


def summarize_costs(
    items: Sequence[TripItem],
    *,
    trip_type: TripType,
    planned_budget: Decimal | None,
    trip_days: int,
) -> CostSummary:
    """Kosztorys całej podróży.

    Sekcje niedostępne dla typu podróży są pomijane (chyba że mimo to mają pozycje).
    """
    if trip_days < 1:
        raise ValueError("Podróż musi trwać co najmniej jeden dzień.")
    by_section: dict[Section, list[TripItem]] = {section: [] for section in Section}
    for item in items:
        by_section[item.get_section()].append(item)

    sections = tuple(
        summarize_section(section, by_section[section])
        for section in Section
        if is_section_allowed(section, trip_type) or by_section[section]
    )
    ratings = [item.get_rating() for item in items]
    total = total_cost(items)
    return CostSummary(
        total_cost=total,
        sections=sections,
        average_rating=average_rating(ratings),
        rated_items_count=sum(1 for rating in ratings if rating is not None),
        budget=compare_with_budget(total, planned_budget),
        trip_days=trip_days,
        average_daily_cost=round_half_up(total / Decimal(trip_days)),
    )
