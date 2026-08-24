"""Orchestrate query embedding, hybrid search, fusion, and context expansion."""

import asyncio
from typing import Any

from openai import AsyncOpenAI
from supabase import AsyncClient

from app.config import settings
from app.retrieval import queries
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.models import RankedPassage, RetrievalFilters

DEFAULT_CANDIDATE_LIMIT = 30
DEFAULT_RESULT_LIMIT = 8
DEFAULT_NEIGHBOR_WINDOW = 1


class DocumentRetriever:
    def __init__(
        self,
        client: AsyncClient,
        *,
        openai_client: Any | None = None,
        candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
        result_limit: int = DEFAULT_RESULT_LIMIT,
        neighbor_window: int = DEFAULT_NEIGHBOR_WINDOW,
    ) -> None:
        if candidate_limit < 1 or candidate_limit > 100:
            raise ValueError("candidate_limit must be between 1 and 100")
        if result_limit < 1 or result_limit > candidate_limit:
            raise ValueError("result_limit must be between 1 and candidate_limit")
        if neighbor_window < 0 or neighbor_window > 3:
            raise ValueError("neighbor_window must be between 0 and 3")

        self.client = client
        self.openai_client = openai_client or AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        self.candidate_limit = candidate_limit
        self.result_limit = result_limit
        self.neighbor_window = neighbor_window

    async def retrieve(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        limit: int | None = None,
    ) -> list[RankedPassage]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank")
        selected_limit = self.result_limit if limit is None else limit
        if selected_limit < 1 or selected_limit > self.candidate_limit:
            raise ValueError("limit must be between 1 and candidate_limit")

        embedding_result, lexical_hits = await asyncio.gather(
            self._embed_query(normalized_query),
            queries.full_text_search(
                self.client,
                query=normalized_query,
                limit=self.candidate_limit,
                filters=filters,
            ),
        )
        semantic_hits = await queries.semantic_search(
            self.client,
            query_embedding=embedding_result,
            limit=self.candidate_limit,
            filters=filters,
        )
        ranked = reciprocal_rank_fusion(semantic_hits, lexical_hits)[:selected_limit]
        if not ranked or self.neighbor_window == 0:
            return ranked

        neighbors = await queries.get_neighbors(
            self.client,
            seed_chunk_ids=[item.passage.chunk_id for item in ranked],
            window=self.neighbor_window,
        )
        return [
            item.model_copy(
                update={"neighbors": tuple(neighbors.get(item.passage.chunk_id, []))}
            )
            for item in ranked
        ]

    async def _embed_query(self, query: str) -> list[float]:
        response = await self.openai_client.embeddings.create(
            input=query,
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            encoding_format="float",
        )
        if len(response.data) != 1:
            raise ValueError(f"expected one query embedding, got {len(response.data)}")
        vector = response.data[0].embedding
        if len(vector) != settings.openai_embedding_dimensions:
            raise ValueError(
                f"expected {settings.openai_embedding_dimensions} dimensions, "
                f"got {len(vector)}"
            )
        return vector
