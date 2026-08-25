import asyncio
import uuid

import pytest

from app.assistant.evidence import EvidenceStore
from app.assistant.outputs import (
    EvidenceCitation,
    GroundedAnswer,
    GroundedStatement,
)
from app.grounding.validator import GroundingError, validate_grounded_answer
from tests.assistant.helpers import FakeRetriever, ranked


def answer(chunk_id: uuid.UUID, quote: str) -> GroundedAnswer:
    return GroundedAnswer(
        status="answered",
        statements=(
            GroundedStatement(
                text="Revenue increased.",
                citations=(EvidenceCitation(chunk_id=chunk_id, quote=quote),),
            ),
        ),
    )


def test_accepts_quote_present_in_exposed_passage() -> None:
    evidence = EvidenceStore(FakeRetriever([ranked()]))  # type: ignore[arg-type]
    exposed = asyncio.run(evidence.search("revenue"))[0]

    validate_grounded_answer(
        answer(exposed.chunk_id, "Revenue increased 10% during fiscal 2025."),
        evidence,
    )


def test_rejects_unseen_chunk_and_unsupported_quote() -> None:
    evidence = EvidenceStore(FakeRetriever([ranked()]))  # type: ignore[arg-type]
    exposed = asyncio.run(evidence.search("revenue"))[0]

    with pytest.raises(GroundingError, match="not shown"):
        validate_grounded_answer(
            answer(uuid.UUID("99999999-9999-9999-9999-999999999999"), "Revenue"),
            evidence,
        )
    with pytest.raises(GroundingError, match="not present"):
        validate_grounded_answer(
            answer(exposed.chunk_id, "Operating margin doubled."), evidence
        )


def test_insufficient_evidence_requires_a_search() -> None:
    evidence = EvidenceStore(FakeRetriever([]))  # type: ignore[arg-type]
    output = GroundedAnswer(status="insufficient_evidence", message="Not found.")

    with pytest.raises(GroundingError, match="after searching"):
        validate_grounded_answer(output, evidence)


def test_refusal_does_not_require_retrieval() -> None:
    evidence = EvidenceStore(FakeRetriever([]))  # type: ignore[arg-type]

    validate_grounded_answer(
        GroundedAnswer(status="refused", message="I cannot recommend a stock."),
        evidence,
    )
