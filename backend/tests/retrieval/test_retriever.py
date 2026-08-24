from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.retrieval import retriever
from app.retrieval.models import RetrievalFilters, SourcePassage
from app.retrieval.retriever import DocumentRetriever
from tests.retrieval.helpers import search_hit


class FakeEmbeddings:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [0.25] * 1536
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(embedding=self.vector)])


@pytest.mark.anyio
async def test_retrieve_embeds_fuses_limits_and_attaches_neighbors(monkeypatch) -> None:
    semantic = [search_hit(1), search_hit(2), search_hit(3)]
    lexical = [search_hit(2), search_hit(4)]
    neighbor = SourcePassage.model_validate(search_hit(5).model_dump(exclude={"score"}))
    semantic_search = AsyncMock(return_value=semantic)
    full_text_search = AsyncMock(return_value=lexical)
    get_neighbors = AsyncMock(return_value={search_hit(2).chunk_id: [neighbor]})
    monkeypatch.setattr(retriever.queries, "semantic_search", semantic_search)
    monkeypatch.setattr(retriever.queries, "full_text_search", full_text_search)
    monkeypatch.setattr(retriever.queries, "get_neighbors", get_neighbors)
    embeddings = FakeEmbeddings()
    filters = RetrievalFilters(tickers=("AAPL",), years=(2025,))
    service = DocumentRetriever(
        object(),
        openai_client=SimpleNamespace(embeddings=embeddings),
        candidate_limit=3,
        result_limit=2,
    )

    results = await service.retrieve("  services revenue  ", filters=filters)

    assert [result.passage.chunk_id for result in results] == [
        search_hit(2).chunk_id,
        search_hit(1).chunk_id,
    ]
    assert results[0].neighbors == (neighbor,)
    assert embeddings.calls[0] == {
        "input": "services revenue",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "encoding_format": "float",
    }
    semantic_search.assert_awaited_once_with(
        service.client,
        query_embedding=[0.25] * 1536,
        limit=3,
        filters=filters,
    )
    full_text_search.assert_awaited_once_with(
        service.client,
        query="services revenue",
        limit=3,
        filters=filters,
    )
    get_neighbors.assert_awaited_once()


@pytest.mark.anyio
async def test_retrieve_rejects_blank_query_before_external_calls() -> None:
    embeddings = FakeEmbeddings()
    service = DocumentRetriever(
        object(), openai_client=SimpleNamespace(embeddings=embeddings)
    )

    with pytest.raises(ValueError, match="query must not be blank"):
        await service.retrieve("  ")

    assert embeddings.calls == []


@pytest.mark.anyio
async def test_retrieve_rejects_wrong_embedding_dimensions(monkeypatch) -> None:
    full_text_search = AsyncMock(return_value=[])
    monkeypatch.setattr(retriever.queries, "full_text_search", full_text_search)
    service = DocumentRetriever(
        object(),
        openai_client=SimpleNamespace(embeddings=FakeEmbeddings([0.1, 0.2])),
    )

    with pytest.raises(ValueError, match="expected 1536 dimensions, got 2"):
        await service.retrieve("revenue")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"candidate_limit": 0}, "candidate_limit"),
        ({"candidate_limit": 5, "result_limit": 6}, "result_limit"),
        ({"neighbor_window": 4}, "neighbor_window"),
    ],
)
def test_rejects_invalid_limits(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        DocumentRetriever(object(), openai_client=object(), **kwargs)
