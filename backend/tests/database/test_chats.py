import asyncio
import uuid

from app.database.chats import append_grounded_turn


class FakeClient:
    def __init__(self) -> None:
        self.function = None
        self.parameters = None
        self.executed = False

    def rpc(self, function, parameters):
        self.function = function
        self.parameters = parameters
        return self

    async def execute(self):
        self.executed = True


def test_append_grounded_turn_passes_complete_atomic_payload() -> None:
    client = FakeClient()
    thread_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    citation = {
        "position": 1,
        "chunk_id": "55555555-5555-5555-5555-555555555555",
        "quote": "Revenue increased.",
    }

    asyncio.run(
        append_grounded_turn(
            client,  # type: ignore[arg-type]
            thread_id=thread_id,
            user_message={"role": "user"},
            assistant_message={"role": "assistant"},
            assistant_model="test-model",
            assistant_usage={"input_tokens": 10},
            citations=[citation],
        )
    )

    assert client.function == "append_grounded_chat_turn"
    assert client.parameters == {
        "target_thread_id": str(thread_id),
        "user_message": {"role": "user"},
        "assistant_message": {"role": "assistant"},
        "assistant_model": "test-model",
        "assistant_usage": {"input_tokens": 10},
        "citations": [citation],
    }
    assert client.executed
