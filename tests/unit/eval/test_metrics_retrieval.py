from adaptiverag.eval.metrics import mrr, recall_at_k
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
