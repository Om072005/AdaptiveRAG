from adaptiverag.ingest.graph_cli import best_chunk, relink_plan
from adaptiverag.ingest.resolve import relation_id

SERVING = {"d": [("d:sentence:0", 0, 30), ("d:sentence:1", 31, 80)]}


def rel(rel_id: str, chunk: str, start: int, end: int, conf: float = 0.9, doc: str = "d") -> tuple:  # type: ignore[type-arg]
    return (rel_id, "e_s", "founded", "e_o", chunk, doc, start, end, conf)


def test_the_chunk_with_the_most_shared_characters_wins_and_ties_go_earlier() -> None:
    assert best_chunk(10, 40, SERVING["d"]) == "d:sentence:0"  # 20 characters against 9
    assert best_chunk(25, 70, SERVING["d"]) == "d:sentence:1"
    assert best_chunk(0, 80, [("a", 0, 40), ("b", 40, 80)]) == "a"
    assert best_chunk(90, 95, SERVING["d"]) is None


def test_a_relation_moves_to_its_serving_chunk_and_its_id_follows() -> None:
    moves, dropped, unmatched = relink_plan([rel("r1", "d:fixed:0", 10, 40)], SERVING)
    assert moves == [("r1", relation_id("e_s", "founded", "e_o", "d:sentence:0"), "d:sentence:0")]
    assert dropped == [] and unmatched == []


def test_a_relation_already_on_its_serving_chunk_stays() -> None:
    same = relation_id("e_s", "founded", "e_o", "d:sentence:1")
    assert relink_plan([rel(same, "d:sentence:1", 40, 60)], SERVING) == ([], [], [])


def test_two_copies_of_one_fact_merge_and_the_more_confident_stays() -> None:
    rels = [rel("r1", "d:fixed:0", 5, 20, conf=0.6), rel("r2", "d:fixed:1", 10, 25, conf=0.9)]
    moves, dropped, unmatched = relink_plan(rels, SERVING)
    assert [m[0] for m in moves] == ["r2"] and dropped == ["r1"] and unmatched == []


def test_a_relation_with_no_serving_chunk_is_kept_and_counted() -> None:
    moves, dropped, unmatched = relink_plan([rel("r9", "x:fixed:0", 0, 10, doc="x")], SERVING)
    assert moves == [] and dropped == [] and unmatched == ["r9"]
