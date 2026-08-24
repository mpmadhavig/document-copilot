import uuid

from app.retrieval.models import SearchHit


def search_hit(
    number: int,
    *,
    score: float = 0.5,
    ticker: str = "AAPL",
    chunk_index: int | None = None,
) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.UUID(f"00000000-0000-0000-0000-{number:012d}"),
        document_id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
        chunk_index=number if chunk_index is None else chunk_index,
        content=f"Passage {number}",
        section="Item 7",
        page=10 + number,
        chunk_metadata={"year": 2025, "pages": [10 + number]},
        accession_number="0000320193-25-000079",
        ticker=ticker,
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date="2025-10-31",
        source_url="https://example.com/filing",
        document_metadata={"report_date": "2025-09-27"},
        score=score,
    )
