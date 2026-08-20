from unittest.mock import AsyncMock

import pytest

from app.database import supabase


@pytest.mark.anyio
async def test_create_user_client_uses_anon_key_and_user_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = object()
    create_client = AsyncMock(return_value=client)
    monkeypatch.setattr(supabase, "acreate_client", create_client)

    result = await supabase.create_user_client("user-access-token")

    assert result is client
    create_client.assert_awaited_once()
    url, key = create_client.await_args.args
    options = create_client.await_args.kwargs["options"]
    assert url == "https://example.supabase.co/"
    assert key == "test-anon-key"
    assert options.headers == {"Authorization": "Bearer user-access-token"}
    assert options.auto_refresh_token is False
    assert options.persist_session is False


@pytest.mark.anyio
async def test_create_user_client_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="access_token must not be empty"):
        await supabase.create_user_client("")


@pytest.mark.anyio
async def test_create_service_role_client_uses_service_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = object()
    create_client = AsyncMock(return_value=client)
    monkeypatch.setattr(supabase, "acreate_client", create_client)

    result = await supabase.create_service_role_client()

    assert result is client
    create_client.assert_awaited_once()
    url, key = create_client.await_args.args
    options = create_client.await_args.kwargs["options"]
    assert url == "https://example.supabase.co/"
    assert key == "test-service-role-key"
    assert options.headers == {}
    assert options.auto_refresh_token is False
    assert options.persist_session is False
