import pytest

from adaptiverag.router.hybrid import rrf
from adaptiverag.types import Hit, Route


def hit(chunk_id: str, rank: int, source: Route, score: float = 0.5) -> Hit:
    return Hit(chunk_id, chunk_id.split(":")[0], "T", f"text of {chunk_id}", score, source, rank)


def test_fused_score_is_the_sum_of_reciprocal_ranks() -> None:
    vector = [hit("a:s:0", 1, "vector"), hit("b:s:0", 2, "vector")]
    graph = [hit("b:s:0", 1, "graph"), hit("c:s:0", 2, "graph")]
    fused = rrf([vector, graph], k=60)
    assert [h.chunk_id for h in fused] == ["b:s:0", "a:s:0", "c:s:0"]
    assert fused[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[1].score == pytest.approx(1 / 61)
    assert [h.rank for h in fused] == [1, 2, 3]


def test_duplicate_chunk_ids_are_merged_and_keep_graph_provenance() -> None:
    fused = rrf([[hit("a:s:0", 1, "vector")], [hit("a:s:0", 3, "graph"), hit("g:s:1", 1, "graph")]])
    by_id = {h.chunk_id: h for h in fused}
    assert len(fused) == 2
    assert by_id["a:s:0"].source == "hybrid"
    assert by_id["g:s:1"].source == "graph"


def test_same_chunk_twice_in_one_list_counts_once_at_its_best_rank() -> None:
    graph = [hit("a:s:0", 1, "graph"), hit("a:s:0", 4, "graph")]
    assert rrf([graph], k=60)[0].score == pytest.approx(1 / 61)


def test_ties_keep_first_seen_order() -> None:
    fused = rrf([[hit("v:s:0", 1, "vector")], [hit("g:s:0", 1, "graph")]])
    assert [h.chunk_id for h in fused] == ["v:s:0", "g:s:0"]
    assert fused[0].score == fused[1].score


def test_one_empty_list_passes_the_other_through() -> None:
    vector = [hit("a:s:0", 1, "vector"), hit("b:s:0", 2, "vector")]
    fused = rrf([vector, []])
    assert [(h.chunk_id, h.source, h.rank) for h in fused] == [
        ("a:s:0", "vector", 1),
        ("b:s:0", "vector", 2),
    ]
    assert rrf([[], []]) == []
