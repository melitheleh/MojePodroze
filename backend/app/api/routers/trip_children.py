"""Routery CRUD dla zasobów podróży budowane z jednej fabryki.

Każdy zasób dostaje te same endpointy pod ``/api/trips/{trip_id}/<path>``:
``GET`` (lista), ``POST`` (dodaj), ``GET /{item_id}``, ``PUT`` lub ``PATCH /{item_id}``
(edycja), ``DELETE /{item_id}``.
Dzięki temu zachowanie (autoryzacja, 404 dla cudzych danych, archiwum tylko do odczytu)
jest identyczne dla wszystkich sekcji, a kod nie jest powielany.
"""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Path, Response, status
from pydantic import BaseModel

from app.api.deps import DbSession, OwnedTrip
from app.api.responses import READ, WRITE
from app.schemas.items import (
    ExpenseIn,
    ExpenseOut,
    FlightIn,
    FlightOut,
    MealIn,
    MealOut,
    PlaceIn,
    PlaceOut,
    TransportIn,
    TransportOut,
)
from app.schemas.planning import (
    DiaryEntryIn,
    DiaryEntryOut,
    PackingItemIn,
    PackingItemOut,
    PackingItemPatch,
    PlanPointIn,
    PlanPointOut,
    WishlistItemIn,
    WishlistItemOut,
    WishlistItemPatch,
)
from app.services import children
from app.services.children import ChildResource

ItemId = Annotated[int, Path(ge=1, description="Id elementu.")]
ARCHIVE_NOTE = "Podróż w archiwum → 409 TRIP_ARCHIVED."


@dataclass(frozen=True)
class ChildRouterSpec:
    resource: ChildResource
    path: str
    tag: str
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    out_schema: type[BaseModel]
    list_title: str  # np. "Lista lotów"
    noun: str  # biernik, np. "lot" → "Dodaj lot"
    op_singular: str  # do operationId, np. "flight"
    op_plural: str
    partial_update: bool = False
    create_note: str = ""


def build_child_router(spec: ChildRouterSpec) -> APIRouter:
    router = APIRouter(prefix=f"/trips/{{trip_id}}/{spec.path}", tags=[spec.tag])
    resource = spec.resource
    out_schema = spec.out_schema
    create_schema = spec.create_schema
    update_schema = spec.update_schema

    def list_items(trip: OwnedTrip, db: DbSession) -> Any:
        return [
            out_schema.model_validate(child) for child in children.list_children(db, resource, trip)
        ]

    def create_item(trip: OwnedTrip, db: DbSession, payload: create_schema) -> Any:  # type: ignore[valid-type]
        data = payload.model_dump()  # type: ignore[attr-defined]
        return out_schema.model_validate(children.create_child(db, resource, trip, data))

    def get_item(trip: OwnedTrip, db: DbSession, item_id: ItemId) -> Any:
        return out_schema.model_validate(children.get_child(db, resource, trip, item_id))

    def update_item(
        trip: OwnedTrip,
        db: DbSession,
        item_id: ItemId,
        payload: update_schema,  # type: ignore[valid-type]
    ) -> Any:
        data = payload.model_dump(exclude_unset=spec.partial_update)  # type: ignore[attr-defined]
        return out_schema.model_validate(children.update_child(db, resource, trip, item_id, data))

    def delete_item(trip: OwnedTrip, db: DbSession, item_id: ItemId) -> None:
        children.delete_child(db, resource, trip, item_id)

    create_description = " ".join(part for part in (spec.create_note, ARCHIVE_NOTE) if part)
    update_method = "PATCH" if spec.partial_update else "PUT"
    update_description = (
        "Częściowa zmiana: wysyłasz tylko zmieniane pola."
        if spec.partial_update
        else "Pełna edycja."
    )

    router.add_api_route(
        "",
        list_items,
        methods=["GET"],
        response_model=list[out_schema],  # type: ignore[valid-type]
        summary=spec.list_title,
        responses=READ,
        name=f"list_{spec.op_plural}",
    )
    router.add_api_route(
        "",
        create_item,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=out_schema,
        summary=f"Dodaj {spec.noun}",
        description=create_description,
        responses=WRITE,
        name=f"create_{spec.op_singular}",
    )
    router.add_api_route(
        "/{item_id}",
        get_item,
        methods=["GET"],
        response_model=out_schema,
        summary=f"Pobierz {spec.noun}",
        responses=READ,
        name=f"get_{spec.op_singular}",
    )
    router.add_api_route(
        "/{item_id}",
        update_item,
        methods=[update_method],
        response_model=out_schema,
        summary=f"Edytuj {spec.noun}",
        description=f"{update_description} {ARCHIVE_NOTE}",
        responses=WRITE,
        name=f"update_{spec.op_singular}",
    )
    router.add_api_route(
        "/{item_id}",
        delete_item,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        summary=f"Usuń {spec.noun}",
        description=ARCHIVE_NOTE,
        responses=WRITE,
        name=f"delete_{spec.op_singular}",
    )
    return router


CHILD_ROUTER_SPECS: tuple[ChildRouterSpec, ...] = (
    ChildRouterSpec(
        resource=children.FLIGHTS,
        path="flights",
        tag="Loty",
        create_schema=FlightIn,
        update_schema=FlightIn,
        out_schema=FlightOut,
        list_title="Lista lotów",
        noun="lot",
        op_singular="flight",
        op_plural="flights",
        create_note="Tylko dla podróży zagranicznych (krajowa → 409 SECTION_NOT_ALLOWED).",
    ),
    ChildRouterSpec(
        resource=children.TRANSPORTS,
        path="transports",
        tag="Transport",
        create_schema=TransportIn,
        update_schema=TransportIn,
        out_schema=TransportOut,
        list_title="Lista przejazdów",
        noun="przejazd",
        op_singular="transport",
        op_plural="transports",
    ),
    ChildRouterSpec(
        resource=children.MEALS,
        path="meals",
        tag="Posiłki",
        create_schema=MealIn,
        update_schema=MealIn,
        out_schema=MealOut,
        list_title="Lista posiłków",
        noun="posiłek",
        op_singular="meal",
        op_plural="meals",
        create_note="Ocena posiłku to ocena restauracji (1–5).",
    ),
    ChildRouterSpec(
        resource=children.PLACES,
        path="places",
        tag="Noclegi i atrakcje",
        create_schema=PlaceIn,
        update_schema=PlaceIn,
        out_schema=PlaceOut,
        list_title="Lista noclegów i atrakcji",
        noun="nocleg lub atrakcję",
        op_singular="place",
        op_plural="places",
    ),
    ChildRouterSpec(
        resource=children.EXPENSES,
        path="expenses",
        tag="Wydatki inne",
        create_schema=ExpenseIn,
        update_schema=ExpenseIn,
        out_schema=ExpenseOut,
        list_title="Lista wydatków innych",
        noun="wydatek",
        op_singular="expense",
        op_plural="expenses",
    ),
    ChildRouterSpec(
        resource=children.PLAN_POINTS,
        path="plan-points",
        tag="Plan dnia",
        create_schema=PlanPointIn,
        update_schema=PlanPointIn,
        out_schema=PlanPointOut,
        list_title="Plan dzień po dniu",
        noun="punkt planu",
        op_singular="plan_point",
        op_plural="plan_points",
        create_note="Dzień musi mieścić się w terminie podróży (inaczej 422 DATE_OUTSIDE_TRIP).",
    ),
    ChildRouterSpec(
        resource=children.WISHLIST,
        path="wishlist",
        tag="Chcę odwiedzić",
        create_schema=WishlistItemIn,
        update_schema=WishlistItemPatch,
        out_schema=WishlistItemOut,
        list_title="Lista „chcę odwiedzić”",
        noun="punkt „chcę odwiedzić”",
        op_singular="wishlist_item",
        op_plural="wishlist_items",
        partial_update=True,
    ),
    ChildRouterSpec(
        resource=children.PACKING,
        path="packing-items",
        tag="Lista pakowania",
        create_schema=PackingItemIn,
        update_schema=PackingItemPatch,
        out_schema=PackingItemOut,
        list_title="Lista pakowania",
        noun="rzecz do spakowania",
        op_singular="packing_item",
        op_plural="packing_items",
        partial_update=True,
    ),
    ChildRouterSpec(
        resource=children.DIARY,
        path="diary-entries",
        tag="Pamiętnik",
        create_schema=DiaryEntryIn,
        update_schema=DiaryEntryIn,
        out_schema=DiaryEntryOut,
        list_title="Wpisy pamiętnika",
        noun="wpis w pamiętniku",
        op_singular="diary_entry",
        op_plural="diary_entries",
    ),
)

routers: list[APIRouter] = [build_child_router(spec) for spec in CHILD_ROUTER_SPECS]
