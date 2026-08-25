"""AI SDK UI message stream encoding."""

import json
from collections.abc import Iterator
from typing import Literal

ChatErrorCode = Literal[
    "retrieval_failed",
    "grounding_failed",
    "assistant_failed",
    "persistence_failed",
]

_ERROR_TEXT: dict[ChatErrorCode, str] = {
    "retrieval_failed": "The filing corpus could not be searched. Please try again.",
    "grounding_failed": "The answer did not pass grounding checks. Please try again.",
    "assistant_failed": "A grounded response could not be completed. Please try again.",
    "persistence_failed": "The grounded response could not be saved. Please try again.",
}


def event(part: dict[str, object]) -> str:
    return f"data: {json.dumps(part, separators=(',', ':'))}\n\n"


def error_events(code: ChatErrorCode, reference: str) -> tuple[str, str, str]:
    return (
        event(
            {
                "type": "data-chat-error",
                "data": {"code": code, "reference": reference},
                "transient": True,
            }
        ),
        event({"type": "error", "errorText": _ERROR_TEXT[code]}),
        "data: [DONE]\n\n",
    )


def text_deltas(text: str) -> Iterator[str]:
    words = text.split(" ")
    for index, word in enumerate(words):
        yield word if index == len(words) - 1 else f"{word} "
