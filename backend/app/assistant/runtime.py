"""Application-scoped OpenAI client and document agent."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from openai import AsyncOpenAI
from pydantic_ai import Agent

from app.assistant.agent import create_document_agent, create_openai_model
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings


@dataclass(frozen=True)
class AgentRuntime:
    openai_client: AsyncOpenAI
    agent: Agent[DocumentAgentDeps, GroundedAnswer]


def create_agent_runtime() -> AgentRuntime:
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    return AgentRuntime(
        openai_client=client,
        agent=create_document_agent(create_openai_model(client)),
    )


def get_agent_runtime(request: Request) -> AgentRuntime:
    return request.app.state.agent_runtime


AgentRuntimeDep = Annotated[AgentRuntime, Depends(get_agent_runtime)]
