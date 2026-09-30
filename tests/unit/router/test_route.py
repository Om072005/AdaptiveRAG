from typing import Any

import numpy as np
import pytest

from adaptiverag.config import router_cfg
from adaptiverag.router import route as route_mod
from adaptiverag.router.route import route_and_retrieve
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Classification, Hit, QType, Retrieved, Seed

SEED = Seed("e_tb", "Tim Burton", "PERSON", 0.9, "Tim Burton")


def hit(cid: str, source: Any) -> Hit:
    return Hit(cid, "d", "T", "text", 0.5, source, 1)


class Backends:
    """Stand ins for the embedding, classifier, linking and both backends; counts every call."""

    def __init__(
        self,
        label: QType = "single_hop",
        conf: float = 0.9,
        top: float = 0.8,
        path: bool = True,
        seeds: list[Seed] | None = None,
    ) -> None:
        self.label, self.conf, self.top, self.path = label, conf, top, path
        self.seeds = [SEED] if seeds is None else seeds
        self.calls: list[str] = []

    def install(self, mp: pytest.MonkeyPatch) -> None:
        mp.setattr(route_mod.llm, "embed", self.embed)
        mp.setattr(route_mod, "classify", self.classify)
        mp.setattr(route_mod.graph, "link_entities", self.link)
        mp.setattr(route_mod.vector, "retrieve", self.vector)
        mp.setattr(route_mod.graph, "retrieve_from_seeds", self.graph)
        mp.setattr(route_mod, "merge_rerank", self.merge)
        mp.setattr(route_mod.db, "shared", lambda: None)

    def embed(
        self, texts: list[str], trace: Trace | None = None, kind: str = "document"
    ) -> np.ndarray:
        self.calls.append("embed")
        return np.ones((len(texts), 768), dtype=np.float32)

    def classify(
        self, q: str, qvec: np.ndarray, trace: Trace, method: str | None = None
    ) -> Classification:
        self.calls.append("classify")
        return Classification(self.label, self.conf, {self.label: self.conf}, "rules", 0.0, 0)

    def link(self, q: str, qvec: np.ndarray, trace: Trace) -> list[Seed]:
        self.calls.append("link")
        return self.seeds

    def vector(self, q: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
        self.calls.append("vector")
        return Retrieved([hit("v1", "vector")], [], [], self.top, False, 10)

    def graph(self, c: Any, seeds: list[Seed], k: int, qvec: np.ndarray, trace: Trace) -> Retrieved:
        self.calls.append("graph")
        return Retrieved([hit("g1", "graph")], [], seeds, 0.3, self.path, 20)

    def merge(
        self, v: list[Hit], g: list[Hit], qvec: np.ndarray, k: int, trace: Trace
    ) -> list[Hit]:
        self.calls.append("merge")
        return v + g


def run(mp: pytest.MonkeyPatch, b: Backends, mode: Any = "auto") -> tuple[Any, Retrieved, Trace]:
    b.install(mp)
    trace = Trace("q", mode, "cli")
    decision, retrieved = route_and_retrieve("q", mode, trace)
    return decision, retrieved, trace


def test_confident_single_hop_with_a_good_score_stays_on_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    b = Backends()
    d, r, trace = run(monkeypatch, b)
    assert (d.initial, d.final, d.fallbacks) == ("vector", "vector", [])
    assert d.reasons == ["no_relational_structure"] and d.classification.label == "single_hop"
    assert b.calls == ["embed", "classify", "link", "vector"]
    assert [h.chunk_id for h in r.hits] == ["v1"]
    assert (
        trace.fields["classifier_confidence"] == 0.9
        and trace.fields["classifier_method"] == "rules"
    )
    assert (trace.fields["route_initial"], trace.fields["route_taken"]) == ("vector", "vector")


def test_f1_weak_vector_falls_back_to_hybrid_once_reusing_the_vector_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    b = Backends(top=0.2)
    d, r, trace = run(monkeypatch, b)
    assert (d.initial, d.final, d.fallbacks) == ("vector", "hybrid", ["vector_low_score->hybrid"])
    assert (
        b.calls.count("vector") == 1 and b.calls.count("graph") == 1 and b.calls.count("merge") == 1
    )
    assert [h.chunk_id for h in r.hits] == ["v1", "g1"] and r.top_score == 0.2
    assert trace.fields["fallbacks"] == ["vector_low_score->hybrid"]


def relational_to(route: str, mp: pytest.MonkeyPatch) -> None:
    """Pin [policy] relational_route, so the graph route rows are tested whatever D17 serves."""
    cfg = router_cfg()
    pinned = {**cfg, "policy": {**cfg["policy"], "relational_route": route}}
    mp.setattr(route_mod, "router_cfg", lambda: pinned)


def test_relational_with_seeds_walks_the_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    relational_to("graph", monkeypatch)
    b = Backends(label="multi_hop")
    d, r, _ = run(monkeypatch, b)
    assert (d.initial, d.final) == ("graph", "graph") and d.reasons == ["relational:multi_hop"]
    assert "vector" not in b.calls and b.calls.count("link") == 1
    assert r.seeds == [SEED]


def test_f2_graph_without_a_path_falls_back_to_hybrid(monkeypatch: pytest.MonkeyPatch) -> None:
    relational_to("graph", monkeypatch)
    b = Backends(label="comparison", path=False)
    d, r, _ = run(monkeypatch, b)
    assert (d.initial, d.final, d.fallbacks) == ("graph", "hybrid", ["graph_no_path->hybrid"])
    assert b.calls.count("graph") == 1 and b.calls.count("link") == 1
    assert not r.path_found and r.top_score == 0.8


def test_relational_without_seeds_goes_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    relational_to("graph", monkeypatch)
    d, _, _ = run(monkeypatch, Backends(label="multi_hop", seeds=[]))
    assert d.initial == "vector" and d.reasons == ["entities_not_in_graph"]


def test_relational_route_hybrid_merges_both_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    relational_to("hybrid", monkeypatch)
    b = Backends(label="comparison", seeds=[])
    d, _, _ = run(monkeypatch, b)
    assert (d.initial, d.final, d.fallbacks) == ("hybrid", "hybrid", [])
    assert d.reasons == ["relational:comparison"] and b.calls.count("merge") == 1


def test_an_unsure_classifier_goes_hybrid_and_hybrid_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    b = Backends(label="multi_hop", conf=0.3, top=0.1, path=False)
    d, _, _ = run(monkeypatch, b)
    assert (d.initial, d.final, d.fallbacks) == ("hybrid", "hybrid", [])
    assert d.reasons == ["ambiguous:multi_hop 0.30"]


@pytest.mark.parametrize(
    ("mode", "backends"), [("vector", ["vector"]), ("graph", ["link", "graph"])]
)
def test_forced_routes_skip_the_classifier_and_never_fall_back(
    monkeypatch: pytest.MonkeyPatch, mode: str, backends: list[str]
) -> None:
    b = Backends(top=0.1, path=False)
    d, _, trace = run(monkeypatch, b, mode)
    assert d.classification is None and d.reasons == [f"forced:{mode}"]
    assert (d.initial, d.final, d.fallbacks) == (mode, mode, [])
    assert b.calls == ["embed", *backends]
    assert "classifier_label" not in trace.fields


def test_forced_hybrid_merges_both_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    b = Backends()
    d, r, _ = run(monkeypatch, b, "hybrid")
    assert d.final == "hybrid" and b.calls == ["embed", "vector", "link", "graph", "merge"]


def test_spans_are_flat_and_the_question_is_embedded_once(monkeypatch: pytest.MonkeyPatch) -> None:
    b = Backends(top=0.2)
    _, _, trace = run(monkeypatch, b)
    names = [s["name"] for s in trace.spans]
    assert names == ["classify", "retrieve", "retrieve"]  # vector, then graph for the fallback
    assert b.calls.count("embed") == 1
