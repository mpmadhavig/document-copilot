"""HTTP schemas for the chat API."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ThreadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=300)


class ThreadUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=300)


class ThreadResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class UIMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    role: Literal["user", "assistant", "system"]
    parts: list[dict[str, Any]]


class StoredMessage(UIMessage):
    sequence: int
    created_at: datetime


class ChatStreamRequest(BaseModel):
    thread_id: uuid.UUID = Field(alias="threadId")
    messages: list[UIMessage] = Field(min_length=1)


def stored_message(row: dict[str, Any]) -> StoredMessage:
    content = row["content"]
    return StoredMessage(
        id=content.get("id", str(row["id"])),
        role=row["role"],
        parts=content["parts"],
        sequence=row["sequence"],
        created_at=row["created_at"],
    )


def user_text(message: UIMessage) -> str:
    text = "".join(
        part.get("text", "") for part in message.parts if part.get("type") == "text"
    ).strip()
    if not text:
        raise ValueError("The latest user message must contain a non-empty text part")
    return text
