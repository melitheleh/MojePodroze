"""Kosztorys, rekomendacje, statystyki i ekran główny: odczyt z bazy + obliczenia domenowe."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Trip, TripItem, User
from app.domain.common import trip_length_days
from app.domain.costs import summarize_costs
from app.domain.enums import RecommendationCategory, TripStatus
from app.domain.recommendations import (
    WishlistEntry,
    is_previous_visit,
    pending_wishes,
    rank_recommendations,
    visits_from_items,
)
from app.domain.stats import TravelStatistics, TripCost, build_statistics
from app.domain.status import is_read_only
from app.domain.trips import next_trip_countdown
from app.schemas.dashboard import CountdownOut, DashboardOut, TripsByStatusOut
from app.schemas.insights import (
    BudgetOut,
    PendingWishOut,
    PreviousTripOut,
    RecommendationOut,
    RecommendationsOut,
    SectionSummaryOut,
    TripCostSummaryOut,
)
from app.schemas.trips import TripOut
from app.services.trips import list_trips


def trip_cost_summary(trip: Trip) -> TripCostSummaryOut:
    summary = summarize_costs(
        trip.domain_items(),
        trip_type=trip.trip_type,
        planned_budget=trip.planned_budget,
        trip_days=trip_length_days(trip.start_date, trip.end_date),
    )
    return TripCostSummaryOut(
        trip_id=trip.id,
        trip_status=trip.status,
        is_read_only=is_read_only(trip.status),
        total_cost=summary.total_cost,
        average_rating=summary.average_rating,
        rated_items_count=summary.rated_items_count,
        trip_days=summary.trip_days,
        average_daily_cost=summary.average_daily_cost,
        sections=[SectionSummaryOut.model_validate(section) for section in summary.sections],
        budget=BudgetOut.model_validate(summary.budget),
    )


def recommendations_for(
    db: Session, user: User, trip: Trip, *, min_rating: Decimal, limit: int
) -> RecommendationsOut:
    current = trip.to_snapshot()
    previous = [
        other for other in list_trips(db, user) if is_previous_visit(other.to_snapshot(), current)
    ]
    visits = [
        visit for other in previous for visit in visits_from_items(other.id, other.domain_items())
    ]
    ranked = rank_recommendations(visits, min_rating=min_rating, limit=None)
    restaurants = [r for r in ranked if r.category is RecommendationCategory.RESTAURANT]
    places = [r for r in ranked if r.category is not RecommendationCategory.RESTAURANT]
    wishes = pending_wishes(
        [
            WishlistEntry(other.id, wish.name, wish.visited)
            for other in previous
            for wish in other.wishlist_items
        ],
        current_names=[wish.name for wish in trip.wishlist_items],
    )
    return RecommendationsOut(
        destination_city=trip.destination_city,
        previous_trips=[PreviousTripOut.model_validate(other) for other in previous],
        restaurants=[RecommendationOut.model_validate(r) for r in restaurants[:limit]],
        places=[RecommendationOut.model_validate(r) for r in places[:limit]],
        pending_wishlist=[PendingWishOut.model_validate(w) for w in wishes],
    )


def user_statistics(db: Session, user: User) -> TravelStatistics:
    """Suma kosztów każdej podróży liczona zapytaniem agregującym ``SUM`` w bazie."""
    items = TripItem.__table__
    totals = (
        select(items.c.trip_id, func.sum(items.c.cost).label("total"))
        .group_by(items.c.trip_id)
        .subquery()
    )
    rows = db.execute(
        select(Trip, func.coalesce(totals.c.total, 0))
        .outerjoin(totals, totals.c.trip_id == Trip.id)
        .where(Trip.owner_id == user.id)
    ).all()
    return build_statistics(TripCost(trip.to_snapshot(), Decimal(total)) for trip, total in rows)


def dashboard(db: Session, user: User, today: date) -> DashboardOut:
    trips = list_trips(db, user)
    groups: dict[TripStatus, list[TripOut]] = {status: [] for status in TripStatus}
    for trip in trips:
        groups[trip.status].append(TripOut.model_validate(trip))

    countdown = next_trip_countdown((trip.to_snapshot() for trip in trips), today)
    return DashboardOut(
        trips=TripsByStatusOut(
            planned=groups[TripStatus.PLANNED],
            in_progress=groups[TripStatus.IN_PROGRESS],
            completed=groups[TripStatus.COMPLETED],
            archived=groups[TripStatus.ARCHIVED],
        ),
        countdown=None
        if countdown is None
        else CountdownOut(
            trip_id=countdown.trip.id,
            trip_name=countdown.trip.name,
            destination_city=countdown.trip.destination_city,
            start_date=countdown.trip.start_date,
            days_left=countdown.days_left,
        ),
    )
