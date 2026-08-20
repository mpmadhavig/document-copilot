"""FastAPI dependencies for Supabase-authenticated requests."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AsyncClient
from supabase_auth import User
from supabase_auth.errors import AuthError

from app.database.supabase import create_user_client

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> User:
    """Verify a Supabase access token and return its user."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    client = await create_user_client(credentials.credentials)
    try:
        response = await client.auth.get_user(credentials.credentials)
    except AuthError as error:
        raise unauthorized from error

    if response is None or response.user is None:
        raise unauthorized
    return response.user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_user_client(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> AsyncClient:
    """Return a Supabase client evaluated with the request's access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await create_user_client(credentials.credentials)


UserClient = Annotated[AsyncClient, Depends(get_user_client)]
