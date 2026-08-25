import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pydantic_ai.usage import RunUsage

from app.assistant.outputs import GroundedAnswer
from app.chat import orchestrator
from app.database import chats


class FakeAgent:
    def __init__(self) -> None:
        self.history = None

    async def run(self, prompt, *, deps, message_history, usage_limits):
        self.history = message_history
        assert prompt == "Should I buy ACME?"
        assert deps.evidence.search_count == 0
        assert usage_limits is orchestrator.RUN_LIMITS
        return SimpleNamespace(
            output=GroundedAnswer(
                status="refused", message="I cannot provide a buy recommendation."
            ),
            response=SimpleNamespace(model_name="test-model"),
            usage=RunUsage(requests=1, input_tokens=25, output_tokens=8),
        )


def test_complete_turn_uses_authoritative_history_and_records_usage(monkeypatch) -> None:
    load_messages = AsyncMock(
        return_value=[
            {
                "role": "user",
                "content": {"parts": [{"type": "text", "text": "Earlier"}]},
            }
        ]
    )
    monkeypatch.setattr(chats, "load_messages", load_messages)
    agent = FakeAgent()
    runtime = SimpleNamespace(agent=agent, openai_client=object())
    thread_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    client = object()

    completed = asyncio.run(
        orchestrator.complete_turn(
            runtime,  # type: ignore[arg-type]
            client,  # type: ignore[arg-type]
            user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            thread_id=thread_id,
            prompt="Should I buy ACME?",
        )
    )

    load_messages.assert_awaited_once_with(client, thread_id=thread_id)
    assert len(agent.history) == 1
    assert completed.rendered.text == "I cannot provide a buy recommendation."
    assert completed.usage == {
        "input_tokens": 25,
        "output_tokens": 8,
        "requests": 1,
    }
