import numpy as np

from adaptiverag.ingest.graph_cli import label, precision, sample_merges
from adaptiverag.ingest.resolve import merge_decisions
from adaptiverag.types import Triple

CFG = {"name_sim": 0.92, "embed_sim": 0.88, "person_needs_shared_neighbor": True}


def triple(s: str, st: str, p: str, o: str, ot: str, doc: str) -> Triple:
    return Triple(s, st, p, o, ot, f"{doc}:sentence:0", 0, 10, 0.9)


def test_every_merge_is_recorded_with_the_rule_that_fired() -> None:
    triples = [
        triple("John Smith", "PERSON", "member_of", "Harvard", "ORG", "docA"),
        triple("John Smith", "PERSON", "studied_at", "Harvard", "ORG", "docB"),
        triple("John Smith", "PERSON", "member_of", "Parliament", "ORG", "docC"),
        triple("New York", "PLACE", "near", "Harvard", "ORG", "docA"),
        triple("New York City", "PLACE", "has", "Harvard", "ORG", "docB"),
    ]
    unit = lambda *v: np.array(v, dtype=np.float32) / np.linalg.norm(v)  # noqa: E731
    vecs = {("PLACE", "new york"): unit(1, 0), ("PLACE", "new york city"): unit(0.95, 0.31)}
    got = {
        (d["type"], d["a_doc"], d["b_doc"], d["rule"]) for d in merge_decisions(triples, vecs, CFG)
    }
    assert ("PERSON", "docA", "docB", "name 1.00; shared neighbour") in got
    assert ("PLACE", "docA", "docB", "embedding 0.95") in got
    # docC's John Smith shares no neighbour: no merge, so nothing to label
    assert not any("docC" in (a, b) for t, a, b, _ in got if t == "PERSON")


def decisions(n: int) -> list[dict[str, str]]:
    return [
        {
            "type": "ORG",
            "a": f"A{i}",
            "a_doc": "d1",
            "b": f"A{i} Inc.",
            "b_doc": "d2",
            "rule": "name 1.00",
        }
        for i in range(n)
    ]


def test_the_sample_is_seeded_numbered_and_unlabelled() -> None:
    sample = sample_merges(decisions(150), 100)
    assert len(sample) == 100 and [s["n"] for s in sample] == [str(i) for i in range(1, 101)]
    assert all(s["label"] == "" for s in sample)
    assert sample == sample_merges(list(reversed(decisions(150))), 100)
    assert len(sample_merges(decisions(40), 100)) == 40


def test_precision_counts_only_labelled_items() -> None:
    items = [
        {"type": "PERSON", "rule": "name 1.00; same document", "label": "same"},
        {"type": "ORG", "rule": "embedding 0.91", "label": "different"},
        {"type": "ORG", "rule": "name 0.95", "label": "same"},
        {"type": "ORG", "rule": "name 0.93", "label": ""},
    ]
    p = precision(items)
    assert (p["labelled"], p["same"], p["unlabelled"]) == (3, 2, 1)
    assert p["precision"] == 2 / 3
    assert p["name"]["precision"] == 1.0 and p["embedding"]["precision"] == 0.0
    assert p["person"]["labelled"] == 1
    assert precision([{"type": "ORG", "rule": "name", "label": ""}])["precision"] is None


def test_labelling_walks_open_items_and_saves_each_answer() -> None:
    items = sample_merges(decisions(4), 4)
    for i in items:
        i |= {"a_title": "T", "b_title": "T", "a_context": "c", "b_context": "c"}
    answers = iter(["maybe", "y", "n", "s", "q"])
    saves: list[int] = []
    label(items, lambda _: next(answers), lambda: saves.append(1))
    assert [i["label"] for i in items] == ["same", "different", "", ""]
    assert len(saves) == 2
