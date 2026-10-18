from fastapi import APIRouter

from app.api.routers import (
    auth,
    dashboard,
    dictionaries,
    external,
    insights,
    photos,
    system,
    trip_children,
    trips,
    users,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dictionaries.router)
api_router.include_router(dashboard.router)
api_router.include_router(trips.router)
for child_router in trip_children.routers:
    api_router.include_router(child_router)
api_router.include_router(photos.router)
api_router.include_router(insights.router)
api_router.include_router(external.router)
