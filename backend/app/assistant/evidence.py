"""Bounded, request-scoped registry of evidence exposed to the model."""

import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from app.retrieval.models import RankedPassage, RetrievalFilters, SourcePassage
from app.retrieval.retriever import DocumentRetriever

MAX_SEARCHES = 6
MAX_EXPOSED_PASSAGES = 40
SEARCH_EXCERPT_CHARACTERS = 4000


class EvidenceLimitError(ValueError):
    """Raised when an agent exceeds the bounded evidence budget."""


class EvidencePassage(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID
    ticker: str
    company_name: str
    filing_type: str
    fiscal_year: int | None
    filing_date: str
    page: int | None
    section: str | None
    content: str


@dataclass
class EvidenceStore:
    retriever: DocumentRetriever
    max_searches: int = MAX_SEARCHES
    max_exposed_passages: int = MAX_EXPOSED_PASSAGES
    _search_count: int = 0
    _cache: dict[tuple[object, ...], tuple[EvidencePassage, ...]] = field(
        default_factory=dict
    )
    _passages: dict[uuid.UUID, SourcePassage] = field(default_factory=dict)
    _visible_content: dict[uuid.UUID, str] = field(default_factory=dict)
    _neighbors: dict[uuid.UUID, tuple[uuid.UUID, ...]] = field(default_factory=dict)

    @property
    def search_count(self) -> int:
        return self._search_count

    async def search(
        self,
        query: str,
        *,
        tickers: tuple[str, ...] | None = None,
        years: tuple[int, ...] | None = None,
        filing_types: tuple[str, ...] | None = None,
        limit: int = 8,
    ) -> tuple[EvidencePassage, ...]:
        key = (
            query.strip(),
            tickers,
            years,
            filing_types,
            limit,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        if self._search_count >= self.max_searches:
            raise EvidenceLimitError("search limit reached for this answer")
        self._search_count += 1

        results = await self.retriever.retrieve(
            query,
            filters=RetrievalFilters(
                tickers=tickers,
                years=years,
                filing_types=filing_types,
            ),
            limit=limit,
        )
        visible = tuple(self._register_result(result, query) for result in results)
        self._cache[key] = visible
        return visible

    def read_chunk(self, chunk_id: uuid.UUID) -> EvidencePassage:
        passage = self._passages.get(chunk_id)
        if passage is None:
            raise KeyError("chunk is not available from a prior search")
        self._expose(passage, passage.content)
        return _tool_passage(passage, passage.content)

    def read_surrounding_chunks(
        self, chunk_id: uuid.UUID
    ) -> tuple[EvidencePassage, ...]:
        neighbor_ids = self._neighbors.get(chunk_id)
        if neighbor_ids is None:
            raise KeyError("chunk has no surrounding context from a prior search")
        passages = tuple(self._passages[neighbor_id] for neighbor_id in neighbor_ids)
        for passage in passages:
            self._expose(passage, passage.content)
        return tuple(_tool_passage(passage, passage.content) for passage in passages)

    def exposed_passage(self, chunk_id: uuid.UUID) -> SourcePassage | None:
        if chunk_id not in self._visible_content:
            return None
        return self._passages[chunk_id]

    def exposed_content(self, chunk_id: uuid.UUID) -> str | None:
        return self._visible_content.get(chunk_id)

    def _register_result(
        self, result: RankedPassage, query: str
    ) -> EvidencePassage:
        passage = result.passage
        excerpt = _relevant_excerpt(passage.content, query)
        self._passages[passage.chunk_id] = passage
        self._expose(passage, excerpt)
        neighbor_ids: list[uuid.UUID] = []
        for neighbor in result.neighbors:
            self._passages[neighbor.chunk_id] = neighbor
            neighbor_ids.append(neighbor.chunk_id)
        self._neighbors[passage.chunk_id] = tuple(neighbor_ids)
        return _tool_passage(passage, excerpt)

    def _expose(self, passage: SourcePassage, content: str) -> None:
        if (
            passage.chunk_id not in self._visible_content
            and len(self._visible_content) >= self.max_exposed_passages
        ):
            raise EvidenceLimitError("evidence passage limit reached for this answer")
        self._visible_content[passage.chunk_id] = content


def _tool_passage(passage: SourcePassage, content: str) -> EvidencePassage:
    year = passage.chunk_metadata.get("year")
    return EvidencePassage(
        chunk_id=passage.chunk_id,
        ticker=passage.ticker,
        company_name=passage.company_name,
        filing_type=passage.filing_type,
        fiscal_year=year if isinstance(year, int) else None,
        filing_date=passage.filing_date.isoformat(),
        page=passage.page,
        section=passage.section,
        content=content,
    )


def _relevant_excerpt(content: str, query: str) -> str:
    if len(content) <= SEARCH_EXCERPT_CHARACTERS:
        return content
    terms = [term.casefold() for term in query.split() if len(term) >= 4]
    folded = content.casefold()
    matches = [folded.find(term) for term in terms]
    first_match = min((index for index in matches if index >= 0), default=0)
    half = SEARCH_EXCERPT_CHARACTERS // 2
    start = max(0, first_match - half)
    end = min(len(content), start + SEARCH_EXCERPT_CHARACTERS)
    start = max(0, end - SEARCH_EXCERPT_CHARACTERS)
    return content[start:end]
