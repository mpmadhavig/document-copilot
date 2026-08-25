import asyncio

from app.assistant.evidence import EvidenceStore
from app.assistant.outputs import (
    EvidenceCitation,
    GroundedAnswer,
    GroundedStatement,
)
from app.grounding.renderer import render_grounded_answer
from tests.assistant.helpers import FakeRetriever, ranked


def test_renderer_deduplicates_citations_and_uses_server_metadata() -> None:
    evidence = EvidenceStore(FakeRetriever([ranked()]))  # type: ignore[arg-type]
    exposed = asyncio.run(evidence.search("revenue"))[0]
    citation = EvidenceCitation(
        chunk_id=exposed.chunk_id,
        quote="Revenue increased 10% during fiscal 2025.",
    )
    output = GroundedAnswer(
        status="answered",
        statements=(
            GroundedStatement(text="Revenue increased.", citations=(citation,)),
            GroundedStatement(text="The increase was 10%.", citations=(citation,)),
        ),
    )

    rendered = render_grounded_answer(output, evidence)

    assert rendered.status == "answered"
    assert rendered.text == "Revenue increased. [1]\n\nThe increase was 10%. [1]"
    assert len(rendered.citations) == 1
    assert rendered.citations[0].ticker == "ACME"
    assert rendered.message_parts()[1] == {
        "type": "data-answer-status",
        "id": "answer-status",
        "data": {"status": "answered"},
    }
    assert rendered.message_parts()[2]["type"] == "data-citation"


def test_renderer_preserves_insufficient_evidence_status() -> None:
    evidence = EvidenceStore(FakeRetriever([]))  # type: ignore[arg-type]
    output = GroundedAnswer(
        status="insufficient_evidence",
        message="The corpus does not contain enough evidence.",
    )

    rendered = render_grounded_answer(output, evidence)

    assert rendered.status == "insufficient_evidence"
    assert rendered.citations == ()
    assert rendered.message_parts()[1]["data"] == {"status": "insufficient_evidence"}
