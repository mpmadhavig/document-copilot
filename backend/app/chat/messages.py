"""Convert persisted UI messages into model history."""

from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)


def stored_messages_to_model_history(
    rows: list[dict[str, Any]],
) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    for row in rows:
        text = _stored_text(row["content"])
        if not text:
            continue
        if row["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(text)]))
        elif row["role"] == "assistant":
            history.append(
                ModelResponse(
                    parts=[TextPart(text)],
                    model_name=row.get("model"),
                )
            )
    return history


def _stored_text(content: dict[str, Any]) -> str:
    return "".join(
        part.get("text", "")
        for part in content.get("parts", [])
        if part.get("type") == "text"
    ).strip()
