"""Persistence operations for chat threads and messages."""

import uuid
from typing import Any

from supabase import AsyncClient

from app.database.supabase import create_service_role_client


async def list_threads(client: AsyncClient) -> list[dict[str, Any]]:
    response = await (
        client.table("chat_threads")
        .select("id,title,created_at,updated_at")
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def create_thread(
    client: AsyncClient, *, user_id: uuid.UUID, title: str
) -> dict[str, Any]:
    response = await (
        client.table("chat_threads")
        .insert({"user_id": str(user_id), "title": title})
        .execute()
    )
    return response.data[0]


async def rename_thread(
    client: AsyncClient, *, thread_id: uuid.UUID, title: str
) -> dict[str, Any]:
    response = await (
        client.table("chat_threads")
        .update({"title": title})
        .eq("id", str(thread_id))
        .execute()
    )
    return response.data[0]


async def get_thread_owner(thread_id: uuid.UUID) -> uuid.UUID | None:
    """Look up ownership outside RLS solely to distinguish 403 from 404."""
    client = await create_service_role_client()
    response = await (
        client.table("chat_threads")
        .select("user_id")
        .eq("id", str(thread_id))
        .maybe_single()
        .execute()
    )
    if response is None or response.data is None:
        return None
    return uuid.UUID(response.data["user_id"])


async def load_messages(
    client: AsyncClient, *, thread_id: uuid.UUID
) -> list[dict[str, Any]]:
    response = await (
        client.table("chat_messages")
        .select("id,role,content,model,usage,sequence,created_at")
        .eq("thread_id", str(thread_id))
        .order("sequence")
        .execute()
    )
    return response.data


async def append_grounded_turn(
    client: AsyncClient,
    *,
    thread_id: uuid.UUID,
    user_message: dict[str, Any],
    assistant_message: dict[str, Any],
    assistant_model: str,
    assistant_usage: dict[str, Any],
    citations: list[dict[str, Any]],
) -> None:
    await client.rpc(
        "append_grounded_chat_turn",
        {
            "target_thread_id": str(thread_id),
            "user_message": user_message,
            "assistant_message": assistant_message,
            "assistant_model": assistant_model,
            "assistant_usage": assistant_usage,
            "citations": citations,
        },
    ).execute()
