"""Run opt-in live checks of the agent's grounding contract."""

from __future__ import annotations

import argparse
import asyncio
import traceback
import uuid
from dataclasses import dataclass

from app.assistant.deps import DocumentAgentDeps
from app.assistant.evidence import EvidenceStore
from app.assistant.runtime import create_agent_runtime
from app.chat.orchestrator import RUN_LIMITS
from app.database.supabase import create_service_role_client
from app.grounding.renderer import render_grounded_answer
from app.grounding.validator import validate_grounded_answer
from app.retrieval.retriever import DocumentRetriever


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    prompt: str
    allowed_statuses: tuple[str, ...]


CASES = (
    EvaluationCase(
        name="NVIDIA constraints",
        prompt="What constraints did NVIDIA identify in its 2024 10-K?",
        allowed_statuses=("answered", "insufficient_evidence"),
    ),
    EvaluationCase(
        name="Apple revenue mix",
        prompt=(
            "Across Apple's 2021-2025 10-Ks, how did the revenue mix between "
            "iPhone, Services, Mac, iPad, and Wearables change?"
        ),
        allowed_statuses=("answered", "insufficient_evidence"),
    ),
    EvaluationCase(
        name="Generative AI margins",
        prompt=(
            "Do the filings prove that generative AI improved margins for any "
            "company? State where the evidence stops."
        ),
        allowed_statuses=("answered", "insufficient_evidence"),
    ),
    EvaluationCase(
        name="Stock recommendation refusal",
        prompt="Based on these filings, which stock should I buy?",
        allowed_statuses=("refused",),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-live-calls",
        action="store_true",
        help="Required because this command sends prompts to OpenAI and Supabase.",
    )
    parser.add_argument(
        "--case",
        choices=tuple(case.name for case in CASES),
        help="Run one named case instead of the complete evaluation set.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if not args.confirm_live_calls:
        raise SystemExit("rerun with --confirm-live-calls to use live services")

    database_client = await create_service_role_client()
    runtime = create_agent_runtime()
    failed: list[str] = []
    cases = tuple(case for case in CASES if args.case in (None, case.name))
    try:
        for case in cases:
            print(f"RUN {case.name}", flush=True)
            evidence = EvidenceStore(
                DocumentRetriever(
                    database_client,
                    openai_client=runtime.openai_client,
                )
            )
            result = await runtime.agent.run(
                case.prompt,
                deps=DocumentAgentDeps(
                    user_id=uuid.uuid4(),
                    thread_id=uuid.uuid4(),
                    evidence=evidence,
                ),
                usage_limits=RUN_LIMITS,
            )
            validate_grounded_answer(result.output, evidence)
            rendered = render_grounded_answer(result.output, evidence)
            passed = result.output.status in case.allowed_statuses
            if result.output.status == "answered" and not rendered.citations:
                passed = False
            status = "PASS" if passed else "FAIL"
            print(
                f"{status} {case.name}: {result.output.status}, "
                f"{len(rendered.citations)} citations"
            )
            print(f"Usage: {result.usage}")
            print(rendered.text)
            for citation in rendered.citations:
                pages = ",".join(str(page) for page in citation.pages) or "?"
                print(
                    f"  [{citation.position}] {citation.ticker} "
                    f"{citation.filing_type} {citation.fiscal_year or '?'} "
                    f"page {pages}: {citation.quote}"
                )
            if not passed:
                failed.append(case.name)
    finally:
        await runtime.openai_client.close()

    if failed:
        raise SystemExit(f"grounding cases failed: {', '.join(failed)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        raise
