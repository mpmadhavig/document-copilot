import asyncio

import pytest

from app.assistant.evidence import EvidenceLimitError, EvidenceStore
from tests.assistant.helpers import FakeRetriever, passage, ranked


def test_search_registers_only_visible_result_content_and_caches() -> None:
    neighbor = passage(2, content="Neighbor-only evidence.")
    retriever = FakeRetriever([ranked(neighbors=(neighbor,))])
    evidence = EvidenceStore(retriever)  # type: ignore[arg-type]

    first = asyncio.run(evidence.search("revenue", tickers=("acme",), limit=1))
    second = asyncio.run(evidence.search("revenue", tickers=("acme",), limit=1))

    assert first == second
    assert len(retriever.calls) == 1
    assert evidence.search_count == 1
    assert evidence.exposed_content(first[0].chunk_id) is not None
    assert evidence.exposed_content(neighbor.chunk_id) is None


def test_neighbor_content_becomes_citable_only_after_read() -> None:
    neighbor = passage(2, content="Neighbor-only evidence.")
    evidence = EvidenceStore(  # type: ignore[arg-type]
        FakeRetriever([ranked(neighbors=(neighbor,))])
    )
    result = asyncio.run(evidence.search("revenue", limit=1))[0]

    surrounding = evidence.read_surrounding_chunks(result.chunk_id)

    assert surrounding[0].content == "Neighbor-only evidence."
    assert evidence.exposed_content(neighbor.chunk_id) == "Neighbor-only evidence."


def test_search_budget_fails_closed() -> None:
    evidence = EvidenceStore(  # type: ignore[arg-type]
        FakeRetriever([]), max_searches=1
    )
    asyncio.run(evidence.search("first"))

    with pytest.raises(EvidenceLimitError, match="search limit"):
        asyncio.run(evidence.search("second"))
