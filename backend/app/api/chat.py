"""Chat thread and streaming endpoints."""

import uuid
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.assistant.runtime import AgentRuntimeDep
from app.auth.dependencies import CurrentUser, UserClient
from app.chat import orchestrator
from app.chat.schemas import (
    ChatStreamRequest,
    StoredMessage,
    ThreadCreate,
    ThreadResponse,
    ThreadUpdate,
    stored_message,
    user_text,
)
from app.chat.streaming import ChatErrorCode, error_events, event, text_deltas
from app.database import chats
from app.grounding.validator import GroundingError
from app.observability import new_error_reference
from app.retrieval.retriever import RetrievalError

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger()


async def _authorize_thread(thread_id: uuid.UUID, user_id: uuid.UUID) -> None:
    owner = await chats.get_thread_owner(thread_id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )
    if owner != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this thread",
        )


@router.get("/threads", response_model=list[ThreadResponse])
async def get_threads(current_user: CurrentUser, client: UserClient) -> list[dict]:
    del current_user
    return await chats.list_threads(client)


@router.post(
    "/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED
)
async def post_thread(
    body: ThreadCreate, current_user: CurrentUser, client: UserClient
) -> dict:
    return await chats.create_thread(
        client, user_id=uuid.UUID(str(current_user.id)), title=body.title
    )


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def patch_thread(
    thread_id: uuid.UUID,
    body: ThreadUpdate,
    current_user: CurrentUser,
    client: UserClient,
) -> dict:
    await _authorize_thread(thread_id, uuid.UUID(str(current_user.id)))
    return await chats.rename_thread(client, thread_id=thread_id, title=body.title)


@router.get("/threads/{thread_id}/messages", response_model=list[StoredMessage])
async def get_messages(
    thread_id: uuid.UUID, current_user: CurrentUser, client: UserClient
) -> list[StoredMessage]:
    await _authorize_thread(thread_id, uuid.UUID(str(current_user.id)))
    rows = await chats.load_messages(client, thread_id=thread_id)
    return [stored_message(row) for row in rows]


@router.post("/stream")
async def stream_chat(
    body: ChatStreamRequest,
    current_user: CurrentUser,
    client: UserClient,
    runtime: AgentRuntimeDep,
) -> StreamingResponse:
    user_id = uuid.UUID(str(current_user.id))
    await _authorize_thread(body.thread_id, user_id)
    latest = body.messages[-1]
    if latest.role != "user":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The latest message must have role 'user'",
        )
    try:
        prompt = user_text(latest)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error

    assistant_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())

    async def generate() -> AsyncIterator[str]:
        yield event({"type": "start", "messageId": assistant_id})
        try:
            completed = await orchestrator.complete_turn(
                runtime,
                client,
                user_id=user_id,
                thread_id=body.thread_id,
                prompt=prompt,
            )
        except RetrievalError as error:
            for item in _stream_failure(
                "retrieval_failed", error, thread_id=body.thread_id
            ):
                yield item
            return
        except (GroundingError, UnexpectedModelBehavior) as error:
            for item in _stream_failure(
                "grounding_failed", error, thread_id=body.thread_id
            ):
                yield item
            return
        except Exception as error:  # noqa: BLE001 - stream boundary must fail closed
            for item in _stream_failure(
                "assistant_failed", error, thread_id=body.thread_id
            ):
                yield item
            return

        assistant_message = {
            "id": assistant_id,
            "role": "assistant",
            "parts": completed.rendered.message_parts(),
        }
        try:
            await chats.append_grounded_turn(
                client,
                thread_id=body.thread_id,
                user_message=latest.model_dump(mode="json"),
                assistant_message=assistant_message,
                assistant_model=completed.model,
                assistant_usage=completed.usage,
                citations=[
                    citation.database_row() for citation in completed.rendered.citations
                ],
            )
        except Exception as error:  # noqa: BLE001 - stream boundary must fail closed
            for item in _stream_failure(
                "persistence_failed", error, thread_id=body.thread_id
            ):
                yield item
            return

        yield event(
            {
                "type": "data-answer-status",
                "id": "answer-status",
                "data": {"status": completed.rendered.status},
            }
        )
        yield event({"type": "text-start", "id": text_id})
        for delta in text_deltas(completed.rendered.text):
            yield event({"type": "text-delta", "id": text_id, "delta": delta})
        yield event({"type": "text-end", "id": text_id})
        for citation in completed.rendered.citations:
            yield event(
                {
                    "type": "data-citation",
                    "id": f"citation-{citation.position}",
                    "data": citation.data(),
                }
            )
        yield event({"type": "finish"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )


def _stream_failure(
    code: ChatErrorCode,
    error: Exception,
    *,
    thread_id: uuid.UUID,
) -> tuple[str, str, str]:
    reference = new_error_reference()
    logger.exception(
        "chat_turn_failed",
        thread_id=str(thread_id),
        error_code=code,
        error_reference=reference,
        error_type=type(error).__name__,
    )
    return error_events(code, reference)
