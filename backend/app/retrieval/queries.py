"""Supabase RPC calls for source-passage retrieval."""

import uuid
from collections import defaultdict

from pydantic import TypeAdapter
from supabase import AsyncClient

from app.retrieval.models import (
    NeighborRow,
    RetrievalFilters,
    SearchHit,
    SourcePassage,
)

_SEARCH_HITS = TypeAdapter(list[SearchHit])
_NEIGHBOR_ROWS = TypeAdapter(list[NeighborRow])


def _filter_params(filters: RetrievalFilters | None) -> dict[str, object]:
    selected = filters or RetrievalFilters()
    return {
        "p_tickers": list(selected.tickers) if selected.tickers else None,
        "p_years": list(selected.years) if selected.years else None,
        "p_filing_types": (
            list(selected.filing_types) if selected.filing_types else None
        ),
    }


def _lexical_query(query: str) -> str:
    return " OR ".join(query.split())


async def semantic_search(
    client: AsyncClient,
    *,
    query_embedding: list[float],
    limit: int,
    filters: RetrievalFilters | None = None,
) -> list[SearchHit]:
    response = await client.rpc(
        "semantic_search_chunks",
        {
            "p_query_embedding": query_embedding,
            "p_match_count": limit,
            **_filter_params(filters),
        },
    ).execute()
    return _SEARCH_HITS.validate_python(response.data or [])


async def full_text_search(
    client: AsyncClient,
    *,
    query: str,
    limit: int,
    filters: RetrievalFilters | None = None,
) -> list[SearchHit]:
    response = await client.rpc(
        "full_text_search_chunks",
        {
            "p_query_text": _lexical_query(query),
            "p_match_count": limit,
            **_filter_params(filters),
        },
    ).execute()
    return _SEARCH_HITS.validate_python(response.data or [])


async def get_neighbors(
    client: AsyncClient,
    *,
    seed_chunk_ids: list[uuid.UUID],
    window: int,
) -> dict[uuid.UUID, list[SourcePassage]]:
    if not seed_chunk_ids or window == 0:
        return {}

    response = await client.rpc(
        "get_chunk_neighbors",
        {
            "p_seed_chunk_ids": [str(chunk_id) for chunk_id in seed_chunk_ids],
            "p_window": window,
        },
    ).execute()
    rows = _NEIGHBOR_ROWS.validate_python(response.data or [])
    grouped: defaultdict[uuid.UUID, list[SourcePassage]] = defaultdict(list)
    for row in rows:
        grouped[row.seed_chunk_id].append(
            SourcePassage.model_validate(row.model_dump(exclude={"seed_chunk_id"}))
        )
    return dict(grouped)
