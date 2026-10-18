"""Stan aplikacji, Swagger/OpenAPI, słowniki i format błędów."""

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_swagger(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_swagger_ui_and_redoc_are_served(client: TestClient) -> None:
    assert "swagger-ui" in client.get("/docs").text
    assert client.get("/redoc").status_code == 200


def test_openapi_describes_user_header_and_unique_operation_ids(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Moje podróże API"
    scheme = schema["components"]["securitySchemes"]["UserIdHeader"]
    assert scheme == {
        "type": "apiKey",
        "in": "header",
        "name": "X-User-Id",
        "description": "Id użytkownika zwrócone przez POST /api/auth/login.",
    }
    operation_ids = [
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    ]
    assert len(operation_ids) == len(set(operation_ids))
    declared_tags = {tag["name"] for tag in schema["tags"]}
    used_tags = {
        tag for path in schema["paths"].values() for op in path.values() for tag in op["tags"]
    }
    assert used_tags <= declared_tags


def test_protected_operations_declare_security(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "security" in paths["/api/trips"]["get"]
    assert "security" not in paths["/api/auth/login"]["post"]
    assert "security" not in paths["/api/dictionaries"]["get"]


def test_unknown_route_uses_common_error_format(client: TestClient) -> None:
    response = client.get("/api/nie-ma-takiego")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "HTTP_404"}


def test_method_not_allowed_uses_common_error_format(client: TestClient) -> None:
    response = client.patch("/api/health")
    assert response.status_code == 405
    assert response.json()["code"] == "HTTP_405"


def test_dictionaries_are_public_and_seeded(client: TestClient) -> None:
    response = client.get("/api/dictionaries")
    assert response.status_code == 200
    body = response.json()
    characters = [entry["name"] for entry in body["trip_characters"]]
    assert characters[:4] == ["Góry", "Morze", "Miasto", "Jeziora"]
    assert {"Samochód", "Pociąg", "Autobus", "Prom", "Taksówka"} <= {
        entry["name"] for entry in body["transport_means"]
    }
    assert "Pamiątki" in [entry["name"] for entry in body["expense_categories"]]
    assert body["trip_statuses"] == [
        {"value": "planned", "label": "w planie"},
        {"value": "in_progress", "label": "w trakcie"},
        {"value": "completed", "label": "zrealizowana"},
        {"value": "archived", "label": "archiwum"},
    ]
    assert [t["value"] for t in body["trip_types"]] == ["domestic", "foreign"]
    assert [c["value"] for c in body["currencies"]] == ["EUR", "USD", "GBP"]
    assert len(body["sections"]) == 5
    assert len(body["place_kinds"]) == 2


def test_cors_allows_vite_dev_server(client: TestClient) -> None:
    response = client.options(
        "/api/trips",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-User-Id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
