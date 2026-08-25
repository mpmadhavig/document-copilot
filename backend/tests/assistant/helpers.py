import uuid
from datetime import date

from app.retrieval.models import RankedPassage, SourcePassage


class FakeRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def retrieve(self, query, *, filters, limit):
        self.calls.append((query, filters, limit))
        return self.results


def passage(
    number: int = 1,
    *,
    content: str = "Revenue increased 10% during fiscal 2025.",
    page: int = 42,
) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.UUID(f"00000000-0000-0000-0000-{number:012d}"),
        document_id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
        chunk_index=number,
        content=content,
        section="Item 7",
        page=page,
        chunk_metadata={"year": 2025, "pages": [page]},
        accession_number="0000000000-25-000001",
        ticker="ACME",
        company_name="Acme Corp.",
        filing_type="10-K",
        filing_date=date(2025, 12, 31),
        source_url="https://example.com/filing",
        document_metadata={},
    )


def ranked(
    number: int = 1,
    *,
    content: str = "Revenue increased 10% during fiscal 2025.",
    neighbors: tuple[SourcePassage, ...] = (),
) -> RankedPassage:
    return RankedPassage(
        passage=passage(number, content=content),
        fused_score=0.5,
        semantic_rank=1,
        lexical_rank=1,
        neighbors=neighbors,
    )
