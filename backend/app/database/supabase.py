"""Supabase clients for request-scoped and privileged database access."""

from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import settings


def _client_options(*, authorization: str | None = None) -> AsyncClientOptions:
    headers = {"Authorization": authorization} if authorization else {}
    return AsyncClientOptions(
        headers=headers,
        auto_refresh_token=False,
        persist_session=False,
    )


async def create_user_client(access_token: str) -> AsyncClient:
    """Create a client whose PostgREST requests are evaluated with user RLS."""
    if not access_token:
        raise ValueError("access_token must not be empty")

    return await acreate_client(
        str(settings.supabase_url),
        settings.supabase_anon_key.get_secret_value(),
        options=_client_options(authorization=f"Bearer {access_token}"),
    )


async def create_service_role_client() -> AsyncClient:
    """Create a privileged client for trusted server-side operations only."""
    return await acreate_client(
        str(settings.supabase_url),
        settings.supabase_service_role_key.get_secret_value(),
        options=_client_options(),
    )
