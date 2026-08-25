"""PydanticAI document agent and bounded filing tools."""

import uuid
from pathlib import Path
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.evidence import EvidenceLimitError, EvidencePassage
from app.assistant.outputs import GroundedAnswer
from app.config import settings
from app.grounding.validator import GroundingError, validate_grounded_answer

_INSTRUCTIONS_PATH = Path(__file__).with_name("instructions.md")


def create_openai_model(client: AsyncOpenAI) -> OpenAIResponsesModel:
    provider = OpenAIProvider(openai_client=client)
    return OpenAIResponsesModel(
        cast(Any, settings.openai_chat_model),
        provider=provider,
        settings={
            "max_tokens": 5000,
            "parallel_tool_calls": False,
            "openai_store": False,
        },
    )


def create_document_agent(model: Any) -> Agent[DocumentAgentDeps, GroundedAnswer]:
    agent = Agent(
        model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=_INSTRUCTIONS_PATH.read_text(encoding="utf-8"),
        retries={"tools": 2, "output": 2},
    )

    @agent.tool(sequential=True)
    async def search_filings(
        ctx: RunContext[DocumentAgentDeps],
        query: str,
        tickers: list[str] | None = None,
        years: list[int] | None = None,
        filing_types: list[str] | None = None,
        limit: int = 8,
    ) -> tuple[EvidencePassage, ...]:
        """Search filing passages with optional ticker, fiscal-year, and form filters."""
        if limit < 1 or limit > 8:
            raise ModelRetry("limit must be between 1 and 8")
        try:
            return await ctx.deps.evidence.search(
                query,
                tickers=tuple(tickers) if tickers else None,
                years=tuple(years) if years else None,
                filing_types=tuple(filing_types) if filing_types else None,
                limit=limit,
            )
        except (EvidenceLimitError, ValueError) as error:
            raise ModelRetry(str(error)) from error

    @agent.tool(sequential=True)
    async def read_chunk(
        ctx: RunContext[DocumentAgentDeps], chunk_id: uuid.UUID
    ) -> EvidencePassage:
        """Read the complete text of a chunk discovered by a prior search."""
        try:
            return ctx.deps.evidence.read_chunk(chunk_id)
        except (KeyError, EvidenceLimitError) as error:
            raise ModelRetry(str(error)) from error

    @agent.tool(sequential=True)
    async def read_surrounding_chunks(
        ctx: RunContext[DocumentAgentDeps], chunk_id: uuid.UUID
    ) -> tuple[EvidencePassage, ...]:
        """Read neighboring chunks attached to a result from a prior search."""
        try:
            return ctx.deps.evidence.read_surrounding_chunks(chunk_id)
        except (KeyError, EvidenceLimitError) as error:
            raise ModelRetry(str(error)) from error

    @agent.output_validator
    async def validate_output(
        ctx: RunContext[DocumentAgentDeps], output: GroundedAnswer
    ) -> GroundedAnswer:
        try:
            validate_grounded_answer(output, ctx.deps.evidence)
        except GroundingError as error:
            raise ModelRetry(
                f"Citation validation failed: {error}. Regenerate the complete "
                "output. Copy every quote as a short, contiguous substring from "
                "the cited tool content without changing words or punctuation; "
                "omit any statement for which no exact supporting quote exists."
            ) from error
        return output

    return agent
