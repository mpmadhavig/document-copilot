"""Fail-closed validation for model-produced citations."""

import re

from app.assistant.evidence import EvidenceStore
from app.assistant.outputs import GroundedAnswer

_WHITESPACE = re.compile(r"\s+")


class GroundingError(ValueError):
    """Raised when a structured answer is not supported by exposed evidence."""


def validate_grounded_answer(
    answer: GroundedAnswer, evidence: EvidenceStore
) -> None:
    if answer.status == "refused":
        return
    if answer.status == "insufficient_evidence":
        if evidence.search_count == 0:
            raise GroundingError(
                "insufficient evidence may only be returned after searching the corpus"
            )
        return

    for statement_index, statement in enumerate(answer.statements, start=1):
        for citation in statement.citations:
            visible = evidence.exposed_content(citation.chunk_id)
            if visible is None:
                raise GroundingError(
                    f"statement {statement_index} cites a passage not shown by a tool"
                )
            quote = _normalize(citation.quote)
            if not quote:
                raise GroundingError(
                    f"statement {statement_index} contains an empty citation quote"
                )
            if quote not in _normalize(visible):
                raise GroundingError(
                    f"statement {statement_index} quote is not present in the cited passage"
                )


def _normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()
