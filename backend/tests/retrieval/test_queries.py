from types import SimpleNamespace

import pytest

from app.retrieval.models import RetrievalFilters
from app.retrieval.queries import full_text_search, get_neighbors, semantic_search
from tests.retrieval.helpers import search_hit


class FakeRpcRequest:
    def __init__(self, data) -> None:
        self.data = data

    async def execute(self):
        return SimpleNamespace(data=self.data)


class FakeClient:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name: str, params: dict) -> FakeRpcRequest:
        self.calls.append((name, params))
        return FakeRpcRequest(self.responses.get(name, []))


@pytest.mark.anyio
async def test_semantic_search_assembles_filtered_rpc() -> None:
    row = search_hit(1).model_dump(mode="json")
    client = FakeClient({"semantic_search_chunks": [row]})
    filters = RetrievalFilters(
        tickers=(" aapl ",), years=(2024, 2025), filing_types=("10-k",)
    )

    results = await semantic_search(
        client,
        query_embedding=[0.1, 0.2],
        limit=20,
        filters=filters,
    )

    assert results[0].ticker == "AAPL"
    assert client.calls == [
        (
            "semantic_search_chunks",
            {
                "p_query_embedding": [0.1, 0.2],
                "p_match_count": 20,
                "p_tickers": ["AAPL"],
                "p_years": [2024, 2025],
                "p_filing_types": ["10-K"],
            },
        )
    ]


@pytest.mark.anyio
async def test_full_text_search_sends_unfiltered_query() -> None:
    client = FakeClient({})

    results = await full_text_search(client, query="AWS margin", limit=30)

    assert results == []
    assert client.calls == [
        (
            "full_text_search_chunks",
            {
                "p_query_text": "AWS OR margin",
                "p_match_count": 30,
                "p_tickers": None,
                "p_years": None,
                "p_filing_types": None,
            },
        )
    ]


@pytest.mark.anyio
async def test_get_neighbors_groups_passages_by_seed() -> None:
    first = search_hit(1).model_dump(mode="json", exclude={"score"})
    second = search_hit(2).model_dump(mode="json", exclude={"score"})
    first["seed_chunk_id"] = search_hit(9).model_dump(mode="json")["chunk_id"]
    second["seed_chunk_id"] = search_hit(9).model_dump(mode="json")["chunk_id"]
    client = FakeClient({"get_chunk_neighbors": [first, second]})

    result = await get_neighbors(
        client, seed_chunk_ids=[search_hit(9).chunk_id], window=1
    )

    assert [passage.chunk_id for passage in result[search_hit(9).chunk_id]] == [
        search_hit(1).chunk_id,
        search_hit(2).chunk_id,
    ]


@pytest.mark.anyio
async def test_get_neighbors_skips_rpc_for_empty_seeds_or_zero_window() -> None:
    client = FakeClient({})

    assert await get_neighbors(client, seed_chunk_ids=[], window=1) == {}
    assert (
        await get_neighbors(client, seed_chunk_ids=[search_hit(1).chunk_id], window=0)
        == {}
    )
    assert client.calls == []
