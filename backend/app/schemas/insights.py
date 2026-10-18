"""Kosztorys i oceny, rekomendacje, statystyki."""

from datetime import date

from pydantic import BaseModel, computed_field

from app.domain.costs import BudgetAlertLevel
from app.domain.enums import RecommendationCategory, Section, TripStatus
from app.schemas.common import ApiModel, DecimalOut

# --- Kosztorys ------------------------------------------------------------------------------


class SectionSummaryOut(ApiModel):
    section: Section
    total_cost: DecimalOut
    items_count: int
    average_rating: DecimalOut | None
    rated_items_count: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def label(self) -> str:
        return self.section.label


class BudgetOut(ApiModel):
    planned_budget: DecimalOut | None
    spent: DecimalOut
    remaining: DecimalOut | None
    overrun: DecimalOut | None
    usage_percent: DecimalOut | None
    alert_level: BudgetAlertLevel


class CostSummaryOut(ApiModel):
    total_cost: DecimalOut
    average_rating: DecimalOut | None
    rated_items_count: int
    trip_days: int
    average_daily_cost: DecimalOut
    sections: list[SectionSummaryOut]
    budget: BudgetOut


class TripCostSummaryOut(CostSummaryOut):
    trip_id: int
    trip_status: TripStatus
    is_read_only: bool


# --- Rekomendacje ---------------------------------------------------------------------------


class RecommendationOut(ApiModel):
    category: RecommendationCategory
    name: str
    average_rating: DecimalOut
    ratings_count: int
    trip_ids: list[int]


class PendingWishOut(ApiModel):
    name: str
    trip_ids: list[int]


class PreviousTripOut(ApiModel):
    id: int
    name: str
    start_date: date
    end_date: date
    status: TripStatus


class RecommendationsOut(BaseModel):
    destination_city: str
    previous_trips: list[PreviousTripOut]
    restaurants: list[RecommendationOut]
    places: list[RecommendationOut]
    pending_wishlist: list[PendingWishOut]


# --- Statystyki -----------------------------------------------------------------------------


class YearCountOut(ApiModel):
    year: int
    trips_count: int


class CharacterCostOut(ApiModel):
    character: str
    trips_count: int
    total_cost: DecimalOut
    average_cost: DecimalOut
    average_daily_cost: DecimalOut


class StatisticsOut(ApiModel):
    """Statystyki liczone z podróży zrealizowanych i archiwalnych."""

    realized_trips_count: int
    total_cost: DecimalOut
    average_trip_cost: DecimalOut | None
    average_daily_cost: DecimalOut | None
    trips_per_year: list[YearCountOut]
    cost_by_character: list[CharacterCostOut]
