from adaptiverag.eval.metrics import mrr, recall_at_k, sp_precision
from adaptiverag.types import Hit


def hit(title: str, rank: int) -> Hit:
    return Hit(f"{title}:sentence:0", title, title, "text", 0.9, "vector", rank)


HITS = [hit("Distractor", 1), hit("Jane Roe", 2), hit("Other", 3), hit("Acme Rockets", 4)]
GOLD = ["Acme Rockets", "Jane Roe"]


def test_recall_at_k_counts_distinct_titles_in_top_k() -> None:
    assert recall_at_k(HITS, GOLD, 1) == 0.0
    assert recall_at_k(HITS, GOLD, 2) == 0.5
    assert recall_at_k(HITS, GOLD, 4) == 1.0
    assert recall_at_k(HITS, GOLD, 10) == 1.0


def test_recall_at_k_uses_rank_not_list_order_and_ignores_duplicates() -> None:
    shuffled = [HITS[3], HITS[0], HITS[2], HITS[1], hit("Jane Roe", 5)]
    assert recall_at_k(shuffled, GOLD, 2) == 0.5
    assert recall_at_k([hit("Jane Roe", 1), hit("Jane Roe", 2)], GOLD, 2) == 0.5


def test_recall_at_k_empty_inputs() -> None:
    assert recall_at_k([], GOLD, 5) == 0.0
    assert recall_at_k(HITS, [], 5) == 0.0


def test_mrr_is_reciprocal_position_of_first_supporting_hit() -> None:
    assert mrr(HITS, GOLD) == 0.5
    assert mrr([hit("Acme Rockets", 1)], GOLD) == 1.0
    assert mrr(HITS, ["Missing"]) == 0.0
    assert mrr([], GOLD) == 0.0


def chunk(chunk_id: str, text: str, rank: int) -> Hit:
    return Hit(chunk_id, "d1", "Acme Rockets", text, 0.9, "vector", rank)


def test_sp_precision_is_share_of_retrieved_chars_in_supporting_spans() -> None:
    hits = [chunk("d1:fixed:0", "a" * 10, 1), chunk("d2:fixed:0", "b" * 30, 2)]
    assert sp_precision(hits, [("d1:fixed:0", 0, 10)]) == 10 / 40
    assert sp_precision(hits, [("d1:fixed:0", 2, 6), ("d2:fixed:0", 0, 20)]) == 24 / 40


def test_sp_precision_counts_overlapping_spans_once_and_clips_to_chunk() -> None:
    hits = [chunk("d1:fixed:0", "a" * 10, 1)]
    assert sp_precision(hits, [("d1:fixed:0", 0, 6), ("d1:fixed:0", 4, 8)]) == 0.8
    assert sp_precision(hits, [("d1:fixed:0", -5, 50)]) == 1.0


def test_sp_precision_counts_overlapping_chunks_twice_in_denominator() -> None:
    # two fixed chunks share text; both lengths are in the denominator
    hits = [chunk("d1:fixed:0", "a" * 10, 1), chunk("d1:fixed:1", "a" * 10, 2)]
    assert sp_precision(hits, [("d1:fixed:0", 0, 10), ("d1:fixed:1", 0, 10)]) == 1.0
    assert sp_precision(hits, [("d1:fixed:0", 0, 10)]) == 0.5


def test_sp_precision_empty_inputs() -> None:
    assert sp_precision([], [("d1:fixed:0", 0, 10)]) == 0.0
    assert sp_precision([chunk("d1:fixed:0", "abc", 1)], []) == 0.0
    assert sp_precision([chunk("d1:fixed:0", "", 1)], [("d1:fixed:0", 0, 3)]) == 0.0
