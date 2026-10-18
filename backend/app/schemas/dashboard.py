from datetime import date

from pydantic import BaseModel, Field

from app.schemas.trips import TripOut


class TripsByStatusOut(BaseModel):
    planned: list[TripOut] = Field(description="W planie")
    in_progress: list[TripOut] = Field(description="W trakcie")
    completed: list[TripOut] = Field(description="Zrealizowane")
    archived: list[TripOut] = Field(description="Archiwum")


class CountdownOut(BaseModel):
    trip_id: int
    trip_name: str
    destination_city: str
    start_date: date
    days_left: int = Field(description="0 oznacza, że podróż zaczyna się dziś.")


class DashboardOut(BaseModel):
    trips: TripsByStatusOut
    countdown: CountdownOut | None = Field(
        description="Odliczanie do najbliższej podróży „w planie” albo null."
    )
