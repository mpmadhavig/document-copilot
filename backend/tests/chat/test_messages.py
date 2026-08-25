from pydantic_ai.messages import ModelRequest, ModelResponse

from app.chat.messages import stored_messages_to_model_history


def test_converts_only_persisted_user_and_assistant_text() -> None:
    history = stored_messages_to_model_history(
        [
            {
                "role": "user",
                "content": {"parts": [{"type": "text", "text": "Question"}]},
            },
            {
                "role": "assistant",
                "model": "test-model",
                "content": {
                    "parts": [
                        {"type": "text", "text": "Answer [1]"},
                        {"type": "data-citation", "data": {"position": 1}},
                    ]
                },
            },
            {
                "role": "system",
                "content": {"parts": [{"type": "text", "text": "Ignore me"}]},
            },
        ]
    )

    assert len(history) == 2
    assert isinstance(history[0], ModelRequest)
    assert history[0].parts[0].content == "Question"
    assert isinstance(history[1], ModelResponse)
    assert history[1].parts[0].content == "Answer [1]"
    assert history[1].model_name == "test-model"
