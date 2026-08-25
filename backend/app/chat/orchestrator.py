"""Run and validate one grounded document-assistant turn."""

import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from pydantic_ai import UsageLimits
from supabase import AsyncClient

from app.assistant.deps import DocumentAgentDeps
from app.assistant.evidence import EvidenceStore
from app.assistant.runtime import AgentRuntime
from app.chat.messages import stored_messages_to_model_history
from app.config import settings
from app.database import chats
from app.grounding.renderer import RenderedAnswer, render_grounded_answer
from app.grounding.validator import validate_grounded_answer
from app.retrieval.retriever import DocumentRetriever

RUN_LIMITS = UsageLimits(
    request_limit=10,
    tool_calls_limit=12,
    total_tokens_limit=120_000,
    output_tokens_limit=10_000,
)


@dataclass(frozen=True)
class CompletedTurn:
    rendered: RenderedAnswer
    model: str
    usage: dict[str, Any]


async def complete_turn(
    runtime: AgentRuntime,
    client: AsyncClient,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    prompt: str,
) -> CompletedTurn:
    stored_history = await chats.load_messages(client, thread_id=thread_id)
    evidence = EvidenceStore(
        DocumentRetriever(client, openai_client=runtime.openai_client)
    )
    deps = DocumentAgentDeps(
        user_id=user_id,
        thread_id=thread_id,
        evidence=evidence,
    )
    result = await runtime.agent.run(
        prompt,
        deps=deps,
        message_history=stored_messages_to_model_history(stored_history),
        usage_limits=RUN_LIMITS,
    )

    # Keep this independent check even though the agent validator can ask the model
    # to retry. Nothing reaches the caller unless the final result passes again.
    validate_grounded_answer(result.output, evidence)
    return CompletedTurn(
        rendered=render_grounded_answer(result.output, evidence),
        model=result.response.model_name or settings.openai_chat_model,
        usage=_json_usage(result.usage),
    )


def _json_usage(usage: Any) -> dict[str, Any]:
    values = asdict(usage)
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in values.items()
        if value not in (None, {}, 0)
    }
