import pytest

from app.retrieval.fusion import reciprocal_rank_fusion
from tests.retrieval.helpers import search_hit


def test_overlapping_hit_ranks_above_single_source_hits() -> None:
    semantic = [search_hit(1), search_hit(2)]
    lexical = [search_hit(2), search_hit(3)]

    results = reciprocal_rank_fusion(semantic, lexical)

    assert [result.passage.chunk_id for result in results] == [
        search_hit(2).chunk_id,
        search_hit(1).chunk_id,
        search_hit(3).chunk_id,
    ]
    assert results[0].semantic_rank == 2
    assert results[0].lexical_rank == 1


def test_duplicate_in_one_ranking_only_contributes_once() -> None:
    duplicate = search_hit(1)

    results = reciprocal_rank_fusion([duplicate, duplicate], [])

    assert len(results) == 1
    assert results[0].fused_score == pytest.approx(1 / 61)
    assert results[0].semantic_rank == 1


def test_weights_can_prefer_one_retrieval_source() -> None:
    semantic = [search_hit(1)]
    lexical = [search_hit(2)]

    results = reciprocal_rank_fusion(
        semantic, lexical, semantic_weight=2, lexical_weight=1
    )

    assert results[0].passage.chunk_id == search_hit(1).chunk_id


def test_zero_weight_excludes_hits_unique_to_that_source() -> None:
    results = reciprocal_rank_fusion(
        [search_hit(1)], [search_hit(2)], semantic_weight=0
    )

    assert [result.passage.chunk_id for result in results] == [search_hit(2).chunk_id]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"k": 0}, "k must be positive"),
        ({"semantic_weight": -1}, "weights must not be negative"),
        (
            {"semantic_weight": 0, "lexical_weight": 0},
            "at least one weight must be positive",
        ),
    ],
)
def test_rejects_invalid_configuration(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        reciprocal_rank_fusion([], [], **kwargs)
