"""AI SDK UI message stream encoding."""

import json
from collections.abc import Iterator


def event(part: dict[str, object]) -> str:
    return f"data: {json.dumps(part, separators=(',', ':'))}\n\n"


def text_deltas(text: str) -> Iterator[str]:
    words = text.split(" ")
    for index, word in enumerate(words):
        yield word if index == len(words) - 1 else f"{word} "
