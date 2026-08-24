"""Reciprocal Rank Fusion for semantic and lexical results."""

import uuid
from dataclasses import dataclass

from app.retrieval.models import RankedPassage, SearchHit, SourcePassage


@dataclass
class _FusedHit:
    passage: SourcePassage
    fused_score: float = 0
    semantic_rank: int | None = None
    lexical_rank: int | None = None
    semantic_score: float | None = None
    lexical_score: float | None = None


def reciprocal_rank_fusion(
    semantic_hits: list[SearchHit],
    lexical_hits: list[SearchHit],
    *,
    k: int = 60,
    semantic_weight: float = 1,
    lexical_weight: float = 1,
) -> list[RankedPassage]:
    if k <= 0:
        raise ValueError("k must be positive")
    if semantic_weight < 0 or lexical_weight < 0:
        raise ValueError("weights must not be negative")
    if semantic_weight == 0 and lexical_weight == 0:
        raise ValueError("at least one weight must be positive")

    fused: dict[uuid.UUID, _FusedHit] = {}
    _add_ranking(fused, semantic_hits, "semantic", k, semantic_weight)
    _add_ranking(fused, lexical_hits, "lexical", k, lexical_weight)

    ordered = sorted(
        fused.values(),
        key=lambda hit: (
            -hit.fused_score,
            min(
                rank
                for rank in (hit.semantic_rank, hit.lexical_rank)
                if rank is not None
            ),
            str(hit.passage.chunk_id),
        ),
    )
    return [
        RankedPassage(
            passage=hit.passage,
            fused_score=hit.fused_score,
            semantic_rank=hit.semantic_rank,
            lexical_rank=hit.lexical_rank,
            semantic_score=hit.semantic_score,
            lexical_score=hit.lexical_score,
        )
        for hit in ordered
    ]


def _add_ranking(
    fused: dict[uuid.UUID, _FusedHit],
    hits: list[SearchHit],
    source: str,
    k: int,
    weight: float,
) -> None:
    if weight == 0:
        return
    seen: set[uuid.UUID] = set()
    for rank, hit in enumerate(hits, start=1):
        if hit.chunk_id in seen:
            continue
        seen.add(hit.chunk_id)
        current = fused.setdefault(
            hit.chunk_id,
            _FusedHit(passage=SourcePassage.model_validate(hit.model_dump())),
        )
        current.fused_score += weight / (k + rank)
        if source == "semantic":
            current.semantic_rank = rank
            current.semantic_score = hit.score
        else:
            current.lexical_rank = rank
            current.lexical_score = hit.score
