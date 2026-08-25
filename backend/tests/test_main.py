from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_application_lifespan_initializes_agent_runtime() -> None:
    with TestClient(app) as lifespan_client:
        response = lifespan_client.get("/health")

        assert response.status_code == 200
        assert app.state.agent_runtime.agent is not None


def test_local_frontend_origin_is_allowed() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_auth_me_rejects_missing_token() -> None:
    assert client.get("/auth/me").status_code == 401


def test_auth_me_returns_verified_user() -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="user-id", email="analyst@example.com"
    )
    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer verified-token"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-id",
        "email": "analyst@example.com",
    }
