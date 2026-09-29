import random
from typing import Any

import numpy as np
import pytest

from adaptiverag.stores import graph
from adaptiverag.stores.graph import bfs, edge_score, path_found, provenance, retrieve_from_seeds
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Edge, Seed


def edge(rel: str, s: str, o: str, conf: float = 1.0, chunk: str = "") -> Edge:
    return Edge(rel, s, s.upper(), "p", o, o.upper(), chunk or f"d:sentence:{rel}", conf)


def seed(cid: str) -> Seed:
    return Seed(cid, cid.upper(), "PERSON", 0.9, cid)


# a - c - b joins the two seeds; a - d - e goes deeper; e - f is a third hop
TOY = [
    (edge("r1", "a", "c", 1.0), 0.8),  # 0.9
    (edge("r2", "c", "b", 0.8), 0.5),  # 0.6
    (edge("r3", "a", "d", 0.9), 0.0),  # 0.45
    (edge("r4", "d", "e", 1.0), 1.0),  # 1.0
    (edge("r5", "e", "f", 1.0), 1.0),
]


class Graph:
    """A fetch over fixed rows that counts its calls (one per hop)."""

    def __init__(self, rows: list[tuple[Edge, float]]) -> None:
        self.rows, self.calls = rows, 0

    def __call__(self, ids: list[str]) -> list[tuple[Edge, float]]:
        self.calls += 1
        return [(e, c) for e, c in self.rows if e.subject_id in ids or e.object_id in ids]


def rels(p: Any) -> list[str]:
    return [e.rel_id for e in p.edges]


def test_edge_score_follows_d10() -> None:
    assert edge_score(1.0, 1.0) == 1.0
    assert edge_score(0.8, 0.5) == pytest.approx(0.6)
    assert edge_score(0.9, 0.0) == pytest.approx(0.45)


def test_depth_limits_the_hops_and_each_hop_is_one_fetch() -> None:
    fetch = Graph(TOY)
    paths = bfs([seed("a"), seed("b")], fetch, depth=2, fanout=25, max_paths=50)
    assert max(len(p.edges) for p in paths) == 2
    assert all("r5" not in rels(p) for p in paths)
    assert fetch.calls == 2
    one_hop = bfs([seed("a")], Graph(TOY), depth=1, fanout=25, max_paths=50)
    assert sorted(rels(p)[0] for p in one_hop) == ["r1", "r3"]


def test_a_path_joining_two_seeds_ranks_first_and_is_found_once() -> None:
    paths = bfs([seed("a"), seed("b")], Graph(TOY), depth=2, fanout=25, max_paths=50)
    first = paths[0]
    assert first.connects_seeds and sorted(rels(first)) == ["r1", "r2"]
    assert first.score == pytest.approx(0.9 * 0.6)
    assert sum(sorted(rels(p)) == ["r1", "r2"] for p in paths) == 1
    others = [p for p in paths[1:] if not p.connects_seeds]
    assert [p.score for p in others] == sorted((p.score for p in others), reverse=True)


def test_single_seed_paths_do_not_count_as_joining() -> None:
    paths = bfs([seed("a")], Graph(TOY), depth=2, fanout=25, max_paths=50)
    assert not any(p.connects_seeds for p in paths)
    deep = next(p for p in paths if rels(p) == ["r3", "r4"])
    assert deep.score == pytest.approx(0.45 * 1.0)


def test_fanout_keeps_the_best_edges_per_node() -> None:
    star = [(edge(f"s{i:02d}", "a", f"n{i:02d}", conf=1.0 - i / 100), 0.0) for i in range(30)]
    paths = bfs([seed("a")], Graph(star), depth=1, fanout=25, max_paths=100)
    assert len(paths) == 25
    assert sorted(rels(p)[0] for p in paths) == [f"s{i:02d}" for i in range(25)]


def test_order_does_not_depend_on_row_order() -> None:
    shuffled = TOY[:]
    random.Random(7).shuffle(shuffled)
    first = bfs([seed("b"), seed("a")], Graph(TOY), 2, 25, 50)
    second = bfs([seed("a"), seed("b")], Graph(shuffled), 2, 25, 50)
    assert [rels(p) for p in first] == [rels(p) for p in second]


def test_paths_never_revisit_a_node_and_max_paths_cuts() -> None:
    loop = [(edge("x1", "a", "b"), 1.0), (edge("x2", "b", "a"), 1.0)]
    paths = bfs([seed("a")], Graph(loop), depth=2, fanout=25, max_paths=50)
    assert sorted(rels(p) for p in paths) == [["x1"], ["x2"]]
    assert len(bfs([seed("a"), seed("b")], Graph(TOY), 2, 25, max_paths=2)) == 2


def test_no_seeds_no_paths() -> None:
    fetch = Graph(TOY)
    assert bfs([], fetch, 2, 25, 8) == [] and fetch.calls == 0


def test_provenance_cites_each_chunk_once_in_path_order() -> None:
    paths = bfs([seed("a"), seed("b")], Graph(TOY), 2, 25, 50)
    cited = provenance(paths, k=3)
    assert [c for c, _ in cited][:2] == ["d:sentence:r1", "d:sentence:r2"]
    assert len(cited) == 3 and len({c for c, _ in cited}) == 3
    assert cited[0][1] == paths[0].score


def test_path_found_means_joined_seeds_or_a_strong_single_path() -> None:
    joined = bfs([seed("a"), seed("b")], Graph(TOY), 2, 25, 50)
    assert path_found(joined, min_path_score=0.99)
    single = bfs([seed("a")], Graph(TOY), 1, 25, 50)
    assert path_found(single, min_path_score=0.9)
    assert not path_found(single, min_path_score=0.91)
    assert not path_found([], 0.2)


class FakeConn:
    """Answers the frontier and chunk text queries from fixed rows."""

    def __init__(self) -> None:
        self.rows: list[Any] = []

    def execute(self, sql: str, params: Any) -> "FakeConn":
        if sql == graph.FRONTIER_EDGES:
            ids = params["ids"]
            self.rows = [
                (e.rel_id, e.subject_id, e.subject_name, e.predicate, e.object_id)
                + (e.object_name, e.chunk_id, e.confidence, c)
                for e, c in TOY
                if e.subject_id in ids or e.object_id in ids
            ]
        else:
            self.rows = [(cid, "d", "Title", f"text of {cid}") for cid in params[0]]
        return self

    def fetchall(self) -> list[Any]:
        return self.rows


def test_retrieve_from_seeds_turns_paths_into_hits_and_fills_the_trace() -> None:
    trace = Trace("q", "graph", "cli")
    r = retrieve_from_seeds(FakeConn(), [seed("a"), seed("b")], 2, np.zeros(768), trace)  # type: ignore[arg-type]
    assert [h.chunk_id for h in r.hits] == ["d:sentence:r1", "d:sentence:r2"]
    assert [h.rank for h in r.hits] == [1, 2] and {h.source for h in r.hits} == {"graph"}
    assert r.path_found and r.top_score == pytest.approx(0.54)
    assert trace.fields["n_results"] == 2 and trace.fields["path_found"] is True
    assert trace.fields["top_score"] == r.top_score
