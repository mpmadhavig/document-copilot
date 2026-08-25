"""Deterministically render validated answers and trusted citation metadata."""

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from app.assistant.evidence import EvidenceStore
from app.assistant.outputs import GroundedAnswer


@dataclass(frozen=True)
class RenderedCitation:
    position: int
    chunk_id: uuid.UUID
    quote: str
    ticker: str
    company_name: str
    filing_type: str
    fiscal_year: int | None
    filing_date: str
    pages: tuple[int, ...]
    section: str | None
    accession_number: str
    source_url: str

    def data(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "chunkId": str(self.chunk_id),
            "quote": self.quote,
            "ticker": self.ticker,
            "companyName": self.company_name,
            "filingType": self.filing_type,
            "fiscalYear": self.fiscal_year,
            "filingDate": self.filing_date,
            "pages": list(self.pages),
            "section": self.section,
            "accessionNumber": self.accession_number,
            "sourceUrl": self.source_url,
        }

    def database_row(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "chunk_id": str(self.chunk_id),
            "quote": self.quote,
        }


@dataclass(frozen=True)
class RenderedAnswer:
    status: Literal["answered", "insufficient_evidence", "refused"]
    text: str
    citations: tuple[RenderedCitation, ...]

    def message_parts(self) -> list[dict[str, Any]]:
        parts: list[dict[str, Any]] = [
            {"type": "text", "text": self.text},
            {
                "type": "data-answer-status",
                "id": "answer-status",
                "data": {"status": self.status},
            },
        ]
        parts.extend(
            {
                "type": "data-citation",
                "id": f"citation-{citation.position}",
                "data": citation.data(),
            }
            for citation in self.citations
        )
        return parts


def render_grounded_answer(
    answer: GroundedAnswer, evidence: EvidenceStore
) -> RenderedAnswer:
    if answer.status != "answered":
        assert answer.message is not None
        return RenderedAnswer(
            status=answer.status,
            text=answer.message.strip(),
            citations=(),
        )

    citations: list[RenderedCitation] = []
    positions: dict[tuple[uuid.UUID, str], int] = {}
    rendered_statements: list[str] = []
    for statement in answer.statements:
        markers: list[str] = []
        for citation in statement.citations:
            key = (citation.chunk_id, citation.quote.strip())
            position = positions.get(key)
            if position is None:
                position = len(citations) + 1
                positions[key] = position
                passage = evidence.exposed_passage(citation.chunk_id)
                assert passage is not None
                pages_value = passage.chunk_metadata.get("pages")
                pages = (
                    tuple(page for page in pages_value if isinstance(page, int))
                    if isinstance(pages_value, list)
                    else (() if passage.page is None else (passage.page,))
                )
                year = passage.chunk_metadata.get("year")
                citations.append(
                    RenderedCitation(
                        position=position,
                        chunk_id=passage.chunk_id,
                        quote=citation.quote.strip(),
                        ticker=passage.ticker,
                        company_name=passage.company_name,
                        filing_type=passage.filing_type,
                        fiscal_year=year if isinstance(year, int) else None,
                        filing_date=passage.filing_date.isoformat(),
                        pages=pages,
                        section=passage.section,
                        accession_number=passage.accession_number,
                        source_url=passage.source_url,
                    )
                )
            marker = f"[{position}]"
            if marker not in markers:
                markers.append(marker)
        rendered_statements.append(f"{statement.text.strip()} {' '.join(markers)}")
    return RenderedAnswer(
        status=answer.status,
        text="\n\n".join(rendered_statements),
        citations=tuple(citations),
    )
