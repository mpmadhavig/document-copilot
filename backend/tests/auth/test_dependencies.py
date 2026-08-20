from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthInvalidJwtError

from app.auth import dependencies


@pytest.fixture
def protected_client() -> tuple[TestClient, AsyncMock]:
    app = FastAPI()
    handler = AsyncMock(return_value={"status": "started"})

    @app.get("/protected", dependencies=[Depends(dependencies.get_current_user)])
    async def protected() -> dict[str, str]:
        return await handler()

    return TestClient(app), handler


def test_missing_token_returns_401_before_handler(
    protected_client: tuple[TestClient, AsyncMock],
) -> None:
    client, handler = protected_client

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    handler.assert_not_awaited()


def test_expired_token_returns_401_before_handler(
    monkeypatch: pytest.MonkeyPatch,
    protected_client: tuple[TestClient, AsyncMock],
) -> None:
    client, handler = protected_client
    auth = SimpleNamespace(
        get_user=AsyncMock(side_effect=AuthInvalidJwtError("JWT expired"))
    )
    monkeypatch.setattr(
        dependencies,
        "create_user_client",
        AsyncMock(return_value=SimpleNamespace(auth=auth)),
    )

    response = client.get(
        "/protected", headers={"Authorization": "Bearer expired-token"}
    )

    assert response.status_code == 401
    handler.assert_not_awaited()


def test_valid_token_returns_current_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id="user-id")
    auth = SimpleNamespace(
        get_user=AsyncMock(return_value=SimpleNamespace(user=user))
    )
    monkeypatch.setattr(
        dependencies,
        "create_user_client",
        AsyncMock(return_value=SimpleNamespace(auth=auth)),
    )
    app = FastAPI()

    @app.get("/me")
    async def me(current_user: dependencies.CurrentUser) -> dict[str, str]:
        return {"id": str(current_user.id)}

    response = TestClient(app).get(
        "/me", headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": "user-id"}
    auth.get_user.assert_awaited_once_with("valid-token")
