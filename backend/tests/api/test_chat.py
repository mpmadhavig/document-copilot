import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.assistant.runtime import get_agent_runtime
from app.auth.dependencies import get_current_user, get_user_client
from app.chat import orchestrator
from app.database import chats
from app.grounding.renderer import RenderedAnswer, RenderedCitation
from app.grounding.validator import GroundingError
from app.main import app
from app.retrieval.retriever import RetrievalError

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
THREAD_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = "2026-08-20T12:00:00Z"


def authenticated_client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=USER_ID)
    app.dependency_overrides[get_user_client] = lambda: object()
    app.dependency_overrides[get_agent_runtime] = lambda: object()
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_list_threads(monkeypatch) -> None:
    list_threads = AsyncMock(
        return_value=[
            {
                "id": str(THREAD_ID),
                "title": "Annual report",
                "created_at": NOW,
                "updated_at": NOW,
            }
        ]
    )
    monkeypatch.setattr(chats, "list_threads", list_threads)
    client = authenticated_client()
    try:
        response = client.get("/chat/threads")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Annual report"
    list_threads.assert_awaited_once()


def test_create_thread_for_authenticated_user(monkeypatch) -> None:
    create_thread = AsyncMock(
        return_value={
            "id": str(THREAD_ID),
            "title": "New chat",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )
    monkeypatch.setattr(chats, "create_thread", create_thread)
    client = authenticated_client()
    try:
        response = client.post("/chat/threads", json={"title": "New chat"})
    finally:
        clear_overrides()

    assert response.status_code == 201
    assert response.json()["id"] == str(THREAD_ID)
    assert create_thread.await_args.kwargs["user_id"] == USER_ID


def test_rename_thread(monkeypatch) -> None:
    rename_thread = AsyncMock(
        return_value={
            "id": str(THREAD_ID),
            "title": "Revenue comparison",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=USER_ID))
    monkeypatch.setattr(chats, "rename_thread", rename_thread)
    client = authenticated_client()
    try:
        response = client.patch(
            f"/chat/threads/{THREAD_ID}",
            json={"title": "Revenue comparison"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()["title"] == "Revenue comparison"
    rename_thread.assert_awaited_once()
    assert rename_thread.await_args.kwargs == {
        "thread_id": THREAD_ID,
        "title": "Revenue comparison",
    }


def test_rename_thread_returns_403_for_another_user(monkeypatch) -> None:
    rename_thread = AsyncMock()
    monkeypatch.setattr(
        chats, "get_thread_owner", AsyncMock(return_value=OTHER_USER_ID)
    )
    monkeypatch.setattr(chats, "rename_thread", rename_thread)
    client = authenticated_client()
    try:
        response = client.patch(
            f"/chat/threads/{THREAD_ID}", json={"title": "Not allowed"}
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    rename_thread.assert_not_awaited()


def test_rename_thread_rejects_blank_title() -> None:
    client = authenticated_client()
    try:
        response = client.patch(f"/chat/threads/{THREAD_ID}", json={"title": "   "})
    finally:
        clear_overrides()

    assert response.status_code == 422


def test_loads_message_history_in_repository_order(monkeypatch) -> None:
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=USER_ID))
    monkeypatch.setattr(
        chats,
        "load_messages",
        AsyncMock(
            return_value=[
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "role": "user",
                    "content": {
                        "id": "ui-message-1",
                        "parts": [{"type": "text", "text": "Hello"}],
                    },
                    "sequence": 1,
                    "created_at": NOW,
                }
            ]
        ),
    )
    client = authenticated_client()
    try:
        response = client.get(f"/chat/threads/{THREAD_ID}/messages")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()[0] == {
        "id": "ui-message-1",
        "role": "user",
        "parts": [{"type": "text", "text": "Hello"}],
        "sequence": 1,
        "created_at": "2026-08-20T12:00:00Z",
    }


def test_returns_403_for_another_users_thread(monkeypatch) -> None:
    monkeypatch.setattr(
        chats, "get_thread_owner", AsyncMock(return_value=OTHER_USER_ID)
    )
    client = authenticated_client()
    try:
        response = client.get(f"/chat/threads/{THREAD_ID}/messages")
    finally:
        clear_overrides()

    assert response.status_code == 403


def test_returns_404_for_missing_thread(monkeypatch) -> None:
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=None))
    client = authenticated_client()
    try:
        response = client.get(f"/chat/threads/{THREAD_ID}/messages")
    finally:
        clear_overrides()

    assert response.status_code == 404


def test_streams_ai_sdk_events_and_persists_completed_turn(monkeypatch) -> None:
    append_turn = AsyncMock()
    citation = RenderedCitation(
        position=1,
        chunk_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        quote="Revenue increased 10%.",
        ticker="ACME",
        company_name="Acme Corp.",
        filing_type="10-K",
        fiscal_year=2025,
        filing_date="2025-12-31",
        pages=(42,),
        section="Item 7",
        accession_number="0000000000-25-000001",
        source_url="https://example.com/filing",
    )
    monkeypatch.setattr(
        orchestrator,
        "complete_turn",
        AsyncMock(
            return_value=orchestrator.CompletedTurn(
                rendered=RenderedAnswer(
                    status="answered",
                    text="Revenue increased 10%. [1]",
                    citations=(citation,),
                ),
                model="test-chat-model",
                usage={"input_tokens": 100, "output_tokens": 20},
            )
        ),
    )
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=USER_ID))
    monkeypatch.setattr(chats, "append_grounded_turn", append_turn)
    user_message = {
        "id": "ui-message-1",
        "role": "user",
        "parts": [{"type": "text", "text": "Compare revenue"}],
    }
    client = authenticated_client()
    try:
        response = client.post(
            "/chat/stream",
            json={"threadId": str(THREAD_ID), "messages": [user_message]},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    lines = [line.removeprefix("data: ") for line in response.text.splitlines() if line]
    events = [json.loads(line) for line in lines[:-1]]
    assert events[0]["type"] == "start"
    answer_status = next(
        event for event in events if event["type"] == "data-answer-status"
    )
    assert answer_status["data"] == {"status": "answered"}
    assert any(event["type"] == "text-delta" for event in events)
    citation_event = next(event for event in events if event["type"] == "data-citation")
    assert citation_event["data"]["chunkId"] == str(citation.chunk_id)
    assert events[-1]["type"] == "finish"
    assert lines[-1] == "[DONE]"
    append_turn.assert_awaited_once()
    assert append_turn.await_args.kwargs["user_message"] == user_message
    assert append_turn.await_args.kwargs["assistant_message"]["role"] == "assistant"
    assert append_turn.await_args.kwargs["assistant_model"] == "test-chat-model"
    assert append_turn.await_args.kwargs["citations"] == [citation.database_row()]


def test_stream_rejects_non_user_latest_message(monkeypatch) -> None:
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=USER_ID))
    client = authenticated_client()
    try:
        response = client.post(
            "/chat/stream",
            json={
                "threadId": str(THREAD_ID),
                "messages": [
                    {
                        "id": "ui-message-1",
                        "role": "assistant",
                        "parts": [{"type": "text", "text": "Hello"}],
                    }
                ],
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (RetrievalError("database password leaked"), "retrieval_failed"),
        (GroundingError("unsupported quote leaked"), "grounding_failed"),
        (
            UnexpectedModelBehavior("output retries leaked"),
            "grounding_failed",
        ),
        (RuntimeError("provider detail leaked"), "assistant_failed"),
    ],
)
def test_stream_exposes_safe_completion_failure_code(
    monkeypatch,
    failure: Exception,
    expected_code: str,
) -> None:
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=USER_ID))
    monkeypatch.setattr(
        orchestrator,
        "complete_turn",
        AsyncMock(side_effect=failure),
    )
    client = authenticated_client()
    try:
        response = client.post(
            "/chat/stream",
            json={
                "threadId": str(THREAD_ID),
                "messages": [
                    {
                        "id": "ui-message-1",
                        "role": "user",
                        "parts": [{"type": "text", "text": "Compare revenue"}],
                    }
                ],
            },
        )
    finally:
        clear_overrides()

    lines = [line.removeprefix("data: ") for line in response.text.splitlines() if line]
    events = [json.loads(line) for line in lines[:-1]]
    error_code = next(event for event in events if event["type"] == "data-chat-error")
    assert error_code["data"]["code"] == expected_code
    assert error_code["data"]["reference"].startswith("be-")
    assert error_code["transient"] is True
    assert "leaked" not in response.text
    assert not any(event["type"] == "text-delta" for event in events)


def test_stream_emits_error_when_completed_turn_cannot_be_persisted(
    monkeypatch,
) -> None:
    monkeypatch.setattr(chats, "get_thread_owner", AsyncMock(return_value=USER_ID))
    monkeypatch.setattr(
        orchestrator,
        "complete_turn",
        AsyncMock(
            return_value=orchestrator.CompletedTurn(
                rendered=RenderedAnswer(
                    status="answered", text="Grounded answer", citations=()
                ),
                model="test-chat-model",
                usage={},
            )
        ),
    )
    monkeypatch.setattr(
        chats,
        "append_grounded_turn",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    client = authenticated_client()
    try:
        response = client.post(
            "/chat/stream",
            json={
                "threadId": str(THREAD_ID),
                "messages": [
                    {
                        "id": "ui-message-1",
                        "role": "user",
                        "parts": [{"type": "text", "text": "Compare revenue"}],
                    }
                ],
            },
        )
    finally:
        clear_overrides()

    lines = [line.removeprefix("data: ") for line in response.text.splitlines() if line]
    events = [json.loads(line) for line in lines[:-1]]
    assert response.status_code == 200
    assert events[-2]["type"] == "data-chat-error"
    assert events[-2]["data"]["code"] == "persistence_failed"
    assert events[-2]["data"]["reference"].startswith("be-")
    assert events[-2]["transient"] is True
    assert events[-1] == {
        "type": "error",
        "errorText": "The grounded response could not be saved. Please try again.",
    }
    assert not any(event["type"] == "text-delta" for event in events)
    assert not any(event["type"] == "finish" for event in events)
    assert lines[-1] == "[DONE]"


def test_chat_routes_require_authentication() -> None:
    assert TestClient(app).get("/chat/threads").status_code == 401
