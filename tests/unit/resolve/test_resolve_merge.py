import hashlib
import random

import numpy as np
import pytest

from adaptiverag.ingest import resolve as resolve_mod
from adaptiverag.ingest.resolve import build_rows, entity_id, normalize_name, resolve
from adaptiverag.types import Triple

CFG = {"name_sim": 0.92, "embed_sim": 0.88, "person_needs_shared_neighbor": True}


def triple(s: str, st: str, p: str, o: str, ot: str, doc: str, conf: float = 0.9) -> Triple:
    return Triple(s, st, p, o, ot, f"{doc}:sentence:0", 0, 10, conf)


def ids_named(entities: list[dict[str, object]], name: str) -> list[object]:
    return [e["canonical_id"] for e in entities if e["canonical_name"] == name]


def test_namesakes_without_shared_context_stay_two_entities_sharing_an_alias() -> None:
    triples = [
        triple("John Smith", "PERSON", "born_in", "Ohio", "PLACE", "docA"),
        triple("John Smith", "PERSON", "member_of", "Harvard", "ORG", "docA"),
        triple("John Smith", "PERSON", "member_of", "Parliament", "ORG", "docB"),
    ]
    entities, aliases, relations = build_rows(triples, {}, CFG)
    plain = "e_" + hashlib.sha1(b"PERSON|john smith").hexdigest()[:12]
    assert ids_named(entities, "John Smith") == [plain, entity_id("PERSON", "John Smith", "docB")]
    shared = [a for a in aliases if a["surface_form"] == "John Smith"]
    assert {a["canonical_id"] for a in shared} == {plain, entity_id("PERSON", "John Smith", "docB")}
    by_object = {r["object_id"]: r["subject_id"] for r in relations}
    assert by_object[entity_id("ORG", "Parliament")] != by_object[entity_id("ORG", "Harvard")]


def test_namesakes_with_a_shared_neighbour_merge() -> None:
    triples = [
        triple("John Smith", "PERSON", "member_of", "Harvard", "ORG", "docA"),
        triple("John Smith", "PERSON", "studied_at", "Harvard", "ORG", "docB"),
    ]
    entities, aliases, relations = build_rows(triples, {}, CFG)
    assert len(ids_named(entities, "John Smith")) == 1
    assert len({r["subject_id"] for r in relations}) == 1


def test_person_guard_can_be_turned_off() -> None:
    triples = [
        triple("John Smith", "PERSON", "born_in", "Ohio", "PLACE", "docA"),
        triple("John Smith", "PERSON", "member_of", "Parliament", "ORG", "docB"),
    ]
    entities, _, _ = build_rows(triples, {}, CFG | {"person_needs_shared_neighbor": False})
    assert len(ids_named(entities, "John Smith")) == 1


def test_company_suffix_merges_and_the_common_form_is_canonical() -> None:
    triples = [
        triple("Apple", "ORG", "based_in", "Cupertino", "PLACE", "docA"),
        triple("Apple", "ORG", "founded_by", "Steve Jobs", "PERSON", "docB"),
        triple("Apple Inc.", "ORG", "makes", "iPhone", "WORK", "docC"),
    ]
    entities, aliases, _ = build_rows(triples, {}, CFG)
    (apple,) = [e for e in entities if e["type"] == "ORG"]
    assert apple["canonical_name"] == "Apple" and apple["canonical_id"] == entity_id("ORG", "Apple")
    forms = {
        a["surface_form"]: a["confidence"]
        for a in aliases
        if a["canonical_id"] == apple["canonical_id"]
    }
    assert forms == {"Apple": 1.0, "Apple Inc.": 1.0}


def test_same_name_different_type_stays_apart() -> None:
    triples = [
        triple("Apple", "ORG", "makes", "iPhone", "WORK", "docA"),
        triple("Apple", "OTHER", "grows_in", "Kazakhstan", "PLACE", "docB"),
    ]
    entities, aliases, _ = build_rows(triples, {}, CFG)
    assert sorted(e["type"] for e in entities if e["canonical_name"] == "Apple") == ["ORG", "OTHER"]
    assert len([a for a in aliases if a["surface_form"] == "Apple"]) == 2


def unit(*xs: float) -> np.ndarray:
    v = np.array(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.mark.parametrize(("second", "merged"), [(unit(0.95, 0.31), True), (unit(0.5, 0.87), False)])
def test_embedding_similarity_merges_names_the_trigrams_miss(
    second: np.ndarray, merged: bool
) -> None:
    triples = [
        triple("New York", "PLACE", "part_of", "United States", "PLACE", "docA"),
        triple("New York City", "PLACE", "has", "Central Park", "PLACE", "docB"),
    ]
    vecs = {("PLACE", "new york"): unit(1, 0), ("PLACE", "new york city"): second}
    entities, aliases, _ = build_rows(triples, vecs, CFG)
    ny = [e for e in entities if e["canonical_name"] in ("New York", "New York City")]
    assert len(ny) == (1 if merged else 2)
    if merged:
        conf = {a["surface_form"]: a["confidence"] for a in aliases}
        assert conf["New York"] == 1.0 or conf["New York City"] == 1.0
        assert min(conf["New York"], conf["New York City"]) == pytest.approx(
            float(unit(1, 0) @ second)
        )


def test_close_embedding_does_not_merge_people_across_documents() -> None:
    triples = [
        triple("John Smith", "PERSON", "born_in", "Ohio", "PLACE", "docA"),
        triple("John Smyth", "PERSON", "born_in", "Kent", "PLACE", "docB"),
        triple("John Smithe", "PERSON", "met", "John Smith", "PERSON", "docA"),
    ]
    close = {
        ("PERSON", "john smith"): unit(1, 0),
        ("PERSON", "john smyth"): unit(0.99, 0.14),
        ("PERSON", "john smithe"): unit(0.99, -0.14),
    }
    entities, _, _ = build_rows(triples, close, CFG)
    names = {e["canonical_name"] for e in entities if e["type"] == "PERSON"}
    # same document merges on the close embedding, the other document stays apart
    assert "John Smyth" in names and len(names) == 2


def test_relations_are_deduplicated_and_self_loops_dropped() -> None:
    triples = [
        triple("Tim Burton", "PERSON", "directed", "Ed Wood", "WORK", "docA", conf=0.7),
        triple("Tim Burton", "PERSON", "directed", "Ed Wood", "WORK", "docA", conf=0.9),
        triple("Apple Inc.", "ORG", "renamed_from", "Apple", "ORG", "docA"),
    ]
    _, _, relations = build_rows(triples, {}, CFG)
    (rel,) = relations
    s, o = entity_id("PERSON", "Tim Burton"), entity_id("WORK", "Ed Wood")
    key = f"{s}|directed|{o}|docA:sentence:0".encode()
    assert rel["rel_id"] == hashlib.sha1(key).hexdigest()[:16]
    assert rel["doc_id"] == "docA" and rel["extraction_confidence"] == 0.9


def test_rows_do_not_depend_on_input_order() -> None:
    triples = [
        triple("John Smith", "PERSON", "born_in", "Ohio", "PLACE", "docA"),
        triple("John Smith", "PERSON", "member_of", "Parliament", "ORG", "docB"),
        triple("Apple Inc.", "ORG", "makes", "iPhone", "WORK", "docC"),
        triple("Apple", "ORG", "based_in", "Cupertino", "PLACE", "docD"),
    ]
    shuffled = triples[:]
    random.Random(7).shuffle(shuffled)
    first, second = build_rows(triples, {}, CFG), build_rows(shuffled, {}, CFG)
    assert first[0] == second[0] and first[1] == second[1]
    assert sorted(r["rel_id"] for r in first[2]) == sorted(r["rel_id"] for r in second[2])


def test_normalize_name_is_idempotent() -> None:
    for raw in ["The Apple Computer Co., Inc.", "J. R. R. Tolkien", "The", "co co", "Beyoncé"]:
        once = normalize_name(raw)
        assert normalize_name(once) == once


def test_resolve_embeds_each_name_once(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[list[str]] = []

    def fake_embed(texts: list[str]) -> np.ndarray:
        sent.append(texts)
        return np.eye(len(texts), 768, dtype=np.float32)

    monkeypatch.setattr(resolve_mod.llm, "embed", fake_embed)
    triples = [
        triple("Apple", "ORG", "based_in", "Cupertino", "PLACE", "docA"),
        triple("Apple", "ORG", "based_in", "Cupertino", "PLACE", "docB"),
    ]
    entities, _, _ = resolve(triples)
    assert sent == [["Apple", "Cupertino"]]
    assert all(e["embedding"] is not None and e["embedding"].shape == (768,) for e in entities)
