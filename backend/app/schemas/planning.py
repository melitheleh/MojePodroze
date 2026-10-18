"""Plan dnia, lista „chcę odwiedzić”, lista pakowania i pamiętnik."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, LongText, Name, Note, PatchBool, PatchName

# --- Plan dnia ------------------------------------------------------------------------------


class PlanPointIn(BaseModel):
    day: date = Field(description="Dzień w terminie podróży.")
    planned_time: time | None = Field(default=None, examples=["10:30"])
    place: Name = Field(examples=["Muzeum Watykańskie"])
    description: Note | None = None


class PlanPointOut(ApiModel):
    id: int
    trip_id: int
    day: date
    planned_time: time | None
    place: str
    description: str | None


# --- Chcę odwiedzić -------------------------------------------------------------------------


class WishlistItemIn(BaseModel):
    name: Name = Field(examples=["Fontanna di Trevi"])
    note: Note | None = None


class WishlistItemPatch(BaseModel):
    """Częściowa zmiana; zwykle tylko ``{"visited": true}`` (odhaczenie)."""

    name: PatchName = None
    note: Note | None = None
    visited: PatchBool = None


class WishlistItemOut(ApiModel):
    id: int
    trip_id: int
    name: str
    note: str | None
    visited: bool


# --- Lista pakowania ------------------------------------------------------------------------


class PackingItemIn(BaseModel):
    name: Name = Field(examples=["Krem z filtrem"])


class PackingItemPatch(BaseModel):
    name: PatchName = None
    packed: PatchBool = None


class PackingItemOut(ApiModel):
    id: int
    trip_id: int
    name: str
    packed: bool
    is_default: bool = Field(description="Dodane automatycznie (np. paszport dla zagranicznej).")


# --- Pamiętnik ------------------------------------------------------------------------------


class DiaryEntryIn(BaseModel):
    entry_date: date
    title: Name | None = None
    content: LongText


class DiaryEntryOut(ApiModel):
    id: int
    trip_id: int
    entry_date: date
    title: str | None
    content: str
    created_at: datetime
    updated_at: datetime
