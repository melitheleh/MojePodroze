from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["System"])


class HealthOut(BaseModel):
    status: str


@router.get("/health", summary="Sprawdzenie, czy API działa", name="health")
def health() -> HealthOut:
    return HealthOut(status="ok")
