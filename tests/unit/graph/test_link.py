import pytest

from adaptiverag.stores.graph import match_aliases, nearest_seed, pick_seeds
from adaptiverag.stores.trgm import trigrams


def row(surface: str, cid: str, conf: float, sim: float, type_: str = "PERSON") -> tuple:  # type: ignore[type-arg]
    return (surface, cid, surface, type_, conf, sim)


def test_seed_score_is_alias_confidence_times_word_similarity() -> None:
    (s,) = pick_seeds([row("Tim Burton", "e_tb", 0.9, 1.0)], 0.45)
    assert s.canonical_id == "e_tb" and s.score == 0.9 and s.matched == "Tim Burton"


def test_one_seed_per_entity_from_its_best_alias() -> None:
    seeds = pick_seeds([row("Apple", "e_a", 1.0, 0.8), row("Apple Inc.", "e_a", 1.0, 1.0)], 0.45)
    assert [(s.canonical_id, s.matched, s.score) for s in seeds] == [("e_a", "Apple Inc.", 1.0)]


def test_seeds_below_the_bar_are_left_out() -> None:
    assert pick_seeds([row("Burbank", "e_b", 0.5, 0.8)], 0.45) == []  # 0.40
    # the bar is inclusive
    assert pick_seeds([row("Burbank", "e_b", 0.5, 0.9)], 0.45)[0].score == 0.45


def test_a_short_alias_inside_a_longer_match_is_dropped() -> None:
    seeds = pick_seeds([row("Tim", "e_t", 1.0, 1.0), row("Tim Burton", "e_tb", 1.0, 1.0)], 0.45)
    assert [s.canonical_id for s in seeds] == ["e_tb"]
    # kept when the longer name matched worse
    seeds = pick_seeds([row("Tim", "e_t", 1.0, 1.0), row("Tim Burton", "e_tb", 1.0, 0.6)], 0.45)
    assert [s.canonical_id for s in seeds] == ["e_t", "e_tb"]


def test_two_entities_of_a_comparison_are_both_seeds_in_score_order() -> None:
    rows = [row("Ed Wood", "e_ew", 1.0, 0.9, "WORK"), row("Batman", "e_b", 1.0, 1.0, "WORK")]
    assert [s.canonical_id for s in pick_seeds(rows, 0.45)] == ["e_b", "e_ew"]


def test_embedding_fallback_needs_the_same_bar() -> None:
    assert nearest_seed([("e_x", "X", "ORG", 0.7)], 0.45)[0].matched == "embedding"
    assert nearest_seed([("e_x", "X", "ORG", 0.3)], 0.45) == []
    assert nearest_seed([], 0.45) == []


def alias(surface: str, cid: str, conf: float = 1.0) -> tuple:  # type: ignore[type-arg]
    return (surface, cid, surface, "PERSON", conf, frozenset(trigrams(surface.lower())))


def test_python_alias_match_keeps_what_pg_trgm_keeps() -> None:
    rows = [alias("Tim Burton", "e_tb"), alias("Ed Wood", "e_ew"), alias("Batman", "e_b")]
    found = match_aliases(rows, "Did Tim Burton direct Ed Wood?", 0.45)
    assert [(r[1], r[5]) for r in found] == [("e_tb", 1.0), ("e_ew", 1.0)]


def test_python_alias_match_applies_the_bar_inclusively() -> None:
    # word_similarity('word', 'two words') is 0.8 in pg_trgm
    assert match_aliases([alias("word", "e_w")], "two words", 0.8)[0][5] == 0.800000011920929
    assert match_aliases([alias("word", "e_w")], "two words", 0.81) == []


def test_an_empty_alias_table_is_read_again(monkeypatch: pytest.MonkeyPatch) -> None:
    from adaptiverag.stores import graph

    class Conn:
        class info:  # noqa: N801 (psycopg's attribute name)
            dsn = "test-dsn"

        reads = 0

        def execute(self, q: str, params: object = None) -> "Conn":
            Conn.reads += 1
            return self

        def fetchall(self) -> list[tuple[object, ...]]:
            return [] if Conn.reads == 1 else [("Dwell", "e_d", "Dwell", "WORK", 1.0)]

    monkeypatch.setattr(graph, "_aliases", {})
    monkeypatch.setattr(graph, "has_trgm", lambda c: False)
    assert graph.alias_rows(Conn(), "When was Dwell launched?", 0.45) == []  # type: ignore[arg-type]
    assert [r[1] for r in graph.alias_rows(Conn(), "When was Dwell launched?", 0.45)] == ["e_d"]  # type: ignore[arg-type]
