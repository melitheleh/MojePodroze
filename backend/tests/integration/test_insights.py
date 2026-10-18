"""Kosztorys, rekomendacje, statystyki (zapytania agregujące) i ekran główny."""

from fastapi.testclient import TestClient

from tests.integration.helpers import (
    ApiUser,
    add,
    create_trip,
    expense_payload,
    flight_payload,
    meal_payload,
    place_payload,
    set_status,
    transport_payload,
)

# --- Kosztorys ------------------------------------------------------------------------------


def test_cost_summary_of_empty_domestic_trip(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, planned_budget=None)
    summary = client.get(f"/api/trips/{trip['id']}/cost-summary", headers=user.headers).json()
    assert summary["trip_id"] == trip["id"]
    assert summary["trip_status"] == "planned"
    assert summary["total_cost"] == 0
    assert summary["average_rating"] is None
    assert summary["trip_days"] == 5
    assert [s["section"] for s in summary["sections"]] == [
        "transport",
        "meals",
        "places",
        "expenses",
    ]
    assert summary["budget"] == {
        "planned_budget": None,
        "spent": 0,
        "remaining": None,
        "overrun": None,
        "usage_percent": None,
        "alert_level": "no_budget",
    }


def test_cost_summary_of_full_foreign_trip(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, trip_type="foreign", planned_budget=1200)
    trip_id = trip["id"]
    add(client, user, trip_id, "flights", flight_payload(cost=850, rating=4))
    add(client, user, trip_id, "transports", transport_payload(client, cost=0.1, rating=2))
    add(client, user, trip_id, "meals", meal_payload(cost=0.2, rating=5))
    add(client, user, trip_id, "places", place_payload(cost=199.7, rating=None))
    add(client, user, trip_id, "expenses", expense_payload(client, cost=50))

    summary = client.get(f"/api/trips/{trip_id}/cost-summary", headers=user.headers).json()
    assert summary["total_cost"] == 1100.0  # dokładnie, bez błędów float (0.1 + 0.2 + ...)
    sections = {s["section"]: s for s in summary["sections"]}
    assert sections["flights"]["total_cost"] == 850
    assert sections["flights"]["label"] == "Loty"
    assert sections["transport"]["total_cost"] == 0.1
    assert sections["meals"]["average_rating"] == 5
    assert sections["places"]["rated_items_count"] == 0
    assert sections["places"]["average_rating"] is None
    assert sections["expenses"]["items_count"] == 1
    assert summary["average_rating"] == 3.67  # (4 + 2 + 5) / 3
    assert summary["rated_items_count"] == 3
    assert summary["average_daily_cost"] == 220
    assert summary["budget"] == {
        "planned_budget": 1200,
        "spent": 1100,
        "remaining": 100,
        "overrun": 0,
        "usage_percent": 91.67,
        "alert_level": "warning",
    }


def test_cost_summary_shows_budget_overrun(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user, planned_budget=100)
    add(client, user, trip["id"], "expenses", expense_payload(client, cost=101))
    budget = client.get(f"/api/trips/{trip['id']}/cost-summary", headers=user.headers).json()[
        "budget"
    ]
    assert budget["alert_level"] == "exceeded"
    assert budget["overrun"] == 1
    assert budget["remaining"] == 0


# --- Rekomendacje ---------------------------------------------------------------------------


def build_previous_krakow_trip(client: TestClient, user: ApiUser, status: str) -> dict:
    trip = create_trip(
        client, user, name="Kraków 2026", start_date="2027-01-10", end_date="2027-01-12"
    )
    trip_id = trip["id"]
    add(client, user, trip_id, "meals", meal_payload(restaurant_name="Pod Aniołami", rating=5))
    add(client, user, trip_id, "meals", meal_payload(restaurant_name="Bar Słaby", rating=2))
    add(
        client,
        user,
        trip_id,
        "places",
        place_payload(name="Hotel Wawel", kind="accommodation", rating=4),
    )
    add(client, user, trip_id, "places", place_payload(name="Smocza Jama", rating=5))
    wawel = add(client, user, trip_id, "wishlist", {"name": "Wawel"})
    add(client, user, trip_id, "wishlist", {"name": "Kopiec Kościuszki"})
    add(client, user, trip_id, "wishlist", {"name": "Nowa Huta"})
    client.patch(
        f"/api/trips/{trip_id}/wishlist/{wawel['id']}", json={"visited": True}, headers=user.headers
    )
    if status == "completed":
        set_status(client, user, trip_id, "in_progress", "completed")
    return trip


def test_recommendations_from_previous_trip_to_same_city(
    client: TestClient, user: ApiUser, other_user: ApiUser
) -> None:
    previous = build_previous_krakow_trip(client, user, "completed")
    current = create_trip(client, user, name="Kraków znowu", destination_city="  KRAKÓW ")
    add(client, user, current["id"], "wishlist", {"name": "nowa huta"})
    # cudze dane nie mogą wpływać na rekomendacje
    stranger = create_trip(client, other_user)
    add(client, other_user, stranger["id"], "meals", meal_payload(restaurant_name="Obca", rating=5))
    set_status(client, other_user, stranger["id"], "in_progress")

    response = client.get(f"/api/trips/{current['id']}/recommendations", headers=user.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["destination_city"] == "  KRAKÓW ".strip()
    assert [t["id"] for t in body["previous_trips"]] == [previous["id"]]
    assert body["restaurants"] == [
        {
            "category": "restaurant",
            "name": "Pod Aniołami",
            "average_rating": 5,
            "ratings_count": 1,
            "trip_ids": [previous["id"]],
        }
    ]
    assert [(p["name"], p["category"]) for p in body["places"]] == [
        ("Smocza Jama", "attraction"),
        ("Hotel Wawel", "accommodation"),
    ]
    assert body["pending_wishlist"] == [{"name": "Kopiec Kościuszki", "trip_ids": [previous["id"]]}]


def test_planned_previous_trip_is_not_a_source(client: TestClient, user: ApiUser) -> None:
    build_previous_krakow_trip(client, user, "planned")
    current = create_trip(client, user, name="Kraków znowu")
    body = client.get(f"/api/trips/{current['id']}/recommendations", headers=user.headers).json()
    assert body["previous_trips"] == []
    assert body["restaurants"] == []
    assert body["pending_wishlist"] == []


def test_recommendation_query_parameters(client: TestClient, user: ApiUser) -> None:
    build_previous_krakow_trip(client, user, "completed")
    current = create_trip(client, user, name="Kraków znowu")
    url = f"/api/trips/{current['id']}/recommendations"
    body = client.get(url, params={"min_rating": 2, "limit": 1}, headers=user.headers).json()
    assert [r["name"] for r in body["restaurants"]] == ["Pod Aniołami"]
    assert len(body["places"]) == 1
    assert client.get(url, params={"min_rating": 6}, headers=user.headers).status_code == 422


# --- Statystyki -----------------------------------------------------------------------------


def test_statistics_aggregate_realized_trips(client: TestClient, user: ApiUser) -> None:
    mountains = create_trip(
        client, user, character="mountains", start_date="2026-02-01", end_date="2026-02-04"
    )
    add(client, user, mountains["id"], "expenses", expense_payload(client, cost=1000))
    add(client, user, mountains["id"], "meals", meal_payload(cost=200))
    set_status(client, user, mountains["id"], "in_progress", "completed")

    sea = create_trip(client, user, character="sea", start_date="2027-07-01", end_date="2027-07-06")
    add(client, user, sea["id"], "expenses", expense_payload(client, cost=3000))
    set_status(client, user, sea["id"], "in_progress", "completed", "archived")

    planned = create_trip(client, user, character="sea")
    add(client, user, planned["id"], "expenses", expense_payload(client, cost=99999))

    response = client.get("/api/stats", headers=user.headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["realized_trips_count"] == 2
    assert stats["total_cost"] == 4200
    assert stats["average_trip_cost"] == 2100
    assert stats["average_daily_cost"] == 420  # 4200 / (4 + 6) dni
    assert stats["trips_per_year"] == [
        {"year": 2026, "trips_count": 1},
        {"year": 2027, "trips_count": 1},
    ]
    assert stats["cost_by_character"] == [
        {
            "character": "Góry",
            "trips_count": 1,
            "total_cost": 1200,
            "average_cost": 1200,
            "average_daily_cost": 300,
        },
        {
            "character": "Morze",
            "trips_count": 1,
            "total_cost": 3000,
            "average_cost": 3000,
            "average_daily_cost": 500,
        },
    ]


def test_statistics_of_new_user_are_empty(client: TestClient, user: ApiUser) -> None:
    stats = client.get("/api/stats", headers=user.headers).json()
    assert stats == {
        "realized_trips_count": 0,
        "total_cost": 0,
        "average_trip_cost": None,
        "average_daily_cost": None,
        "trips_per_year": [],
        "cost_by_character": [],
    }


def test_statistics_include_trip_without_items(client: TestClient, user: ApiUser) -> None:
    trip = create_trip(client, user)
    set_status(client, user, trip["id"], "in_progress", "completed")
    stats = client.get("/api/stats", headers=user.headers).json()
    assert stats["realized_trips_count"] == 1
    assert stats["total_cost"] == 0


# --- Ekran główny ---------------------------------------------------------------------------


def test_dashboard_groups_trips_and_counts_down(
    client: TestClient, user: ApiUser, other_user: ApiUser
) -> None:
    far = create_trip(client, user, name="Daleko", start_date="2027-09-01", end_date="2027-09-02")
    near = create_trip(client, user, name="Blisko", start_date="2027-05-01", end_date="2027-05-02")
    started = create_trip(client, user, name="Trwa")
    set_status(client, user, started["id"], "in_progress")
    done = create_trip(client, user, name="Było")
    set_status(client, user, done["id"], "in_progress", "completed")
    old = create_trip(client, user, name="Dawno")
    set_status(client, user, old["id"], "in_progress", "completed", "archived")
    create_trip(client, other_user, name="Cudza", start_date="2027-04-21", end_date="2027-04-22")

    body = client.get("/api/dashboard", headers=user.headers).json()
    groups = {status: [t["name"] for t in trips] for status, trips in body["trips"].items()}
    assert groups == {
        "planned": [near["name"], far["name"]],
        "in_progress": ["Trwa"],
        "completed": ["Było"],
        "archived": ["Dawno"],
    }
    # „dzisiaj” w testach to 2027-04-20
    assert body["countdown"] == {
        "trip_id": near["id"],
        "trip_name": "Blisko",
        "destination_city": "Kraków",
        "start_date": "2027-05-01",
        "days_left": 11,
    }


def test_dashboard_without_upcoming_trip_has_no_countdown(
    client: TestClient, user: ApiUser
) -> None:
    create_trip(client, user, start_date="2027-01-01", end_date="2027-01-02")
    body = client.get("/api/dashboard", headers=user.headers).json()
    assert body["countdown"] is None
    assert len(body["trips"]["planned"]) == 1
