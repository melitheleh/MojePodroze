"""Uniwersalny CRUD dla zasobów należących do podróży (pozycje, plan, listy, pamiętnik).

Każdy zasób opisuje ``ChildResource``: model ORM, kolejność sortowania, opcjonalna sekcja
(sprawdzenie, czy jest dozwolona dla typu podróży) i opcjonalna dodatkowa walidacja.
Wszystkie operacje zapisu sprawdzają regułę „archiwum tylko do odczytu”.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import (
    DayPlanPoint,
    DiaryEntry,
    Expense,
    ExpenseCategory,
    Flight,
    Meal,
    PackingItem,
    Place,
    TransportMean,
    Trip,
    WishlistItem,
)
from app.db.models import (
    Transport as TransportModel,
)
from app.domain.common import ensure_date_within_trip
from app.domain.enums import Section
from app.domain.items import ensure_section_allowed
from app.domain.status import ensure_editable
from app.services.dictionaries import ensure_entry_exists

Validator = Callable[[Session, Trip, Any], None]


@dataclass(frozen=True)
class ChildResource:
    model: type[Any]
    order_by: tuple[Any, ...]
    not_found_message: str
    section: Section | None = None
    validate: Validator | None = None


def list_children(db: Session, resource: ChildResource, trip: Trip) -> Sequence[Any]:
    model = resource.model
    return db.scalars(
        select(model).where(model.trip_id == trip.id).order_by(*resource.order_by)
    ).all()


def get_child(db: Session, resource: ChildResource, trip: Trip, child_id: int) -> Any:
    model = resource.model
    child = db.scalar(select(model).where(model.id == child_id, model.trip_id == trip.id))
    if child is None:
        raise NotFoundError(resource.not_found_message)
    return child


def create_child(db: Session, resource: ChildResource, trip: Trip, data: dict[str, Any]) -> Any:
    ensure_editable(trip.status)
    if resource.section is not None:
        ensure_section_allowed(resource.section, trip.trip_type)
    child = resource.model(trip_id=trip.id, **data)
    if resource.validate is not None:
        resource.validate(db, trip, child)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def update_child(
    db: Session, resource: ChildResource, trip: Trip, child_id: int, data: dict[str, Any]
) -> Any:
    ensure_editable(trip.status)
    child = get_child(db, resource, trip, child_id)
    for field, value in data.items():
        setattr(child, field, value)
    if resource.validate is not None:
        resource.validate(db, trip, child)
    db.commit()
    db.refresh(child)
    return child


def delete_child(db: Session, resource: ChildResource, trip: Trip, child_id: int) -> None:
    ensure_editable(trip.status)
    child = get_child(db, resource, trip, child_id)
    db.delete(child)
    db.commit()


# --- Dodatkowe walidacje --------------------------------------------------------------------


def _validate_transport(db: Session, _trip: Trip, transport: TransportModel) -> None:
    ensure_entry_exists(
        db, TransportMean, transport.transport_mean_id, "Wybrany środek transportu nie istnieje."
    )


def _validate_expense(db: Session, _trip: Trip, expense: Expense) -> None:
    ensure_entry_exists(
        db, ExpenseCategory, expense.category_id, "Wybrana kategoria wydatku nie istnieje."
    )


def _validate_plan_point(_db: Session, trip: Trip, point: DayPlanPoint) -> None:
    ensure_date_within_trip(point.day, trip.start_date, trip.end_date)


# --- Definicje zasobów ----------------------------------------------------------------------

FLIGHTS = ChildResource(
    model=Flight,
    order_by=(Flight.departure_at, Flight.id),
    not_found_message="Nie znaleziono lotu.",
    section=Section.FLIGHTS,
)
TRANSPORTS = ChildResource(
    model=TransportModel,
    order_by=(TransportModel.travel_date, TransportModel.id),
    not_found_message="Nie znaleziono przejazdu.",
    section=Section.TRANSPORT,
    validate=_validate_transport,
)
MEALS = ChildResource(
    model=Meal,
    order_by=(Meal.meal_date, Meal.id),
    not_found_message="Nie znaleziono posiłku.",
    section=Section.MEALS,
)
PLACES = ChildResource(
    model=Place,
    order_by=(Place.visit_date, Place.id),
    not_found_message="Nie znaleziono noclegu ani atrakcji.",
    section=Section.PLACES,
)
EXPENSES = ChildResource(
    model=Expense,
    order_by=(Expense.expense_date, Expense.id),
    not_found_message="Nie znaleziono wydatku.",
    section=Section.EXPENSES,
    validate=_validate_expense,
)
PLAN_POINTS = ChildResource(
    model=DayPlanPoint,
    order_by=(DayPlanPoint.day, DayPlanPoint.planned_time, DayPlanPoint.id),
    not_found_message="Nie znaleziono punktu planu.",
    validate=_validate_plan_point,
)
WISHLIST = ChildResource(
    model=WishlistItem,
    order_by=(WishlistItem.visited, WishlistItem.id),
    not_found_message="Nie znaleziono punktu z listy „chcę odwiedzić”.",
)
PACKING = ChildResource(
    model=PackingItem,
    order_by=(PackingItem.packed, PackingItem.id),
    not_found_message="Nie znaleziono rzeczy z listy pakowania.",
)
DIARY = ChildResource(
    model=DiaryEntry,
    order_by=(DiaryEntry.entry_date, DiaryEntry.id),
    not_found_message="Nie znaleziono wpisu w pamiętniku.",
)
