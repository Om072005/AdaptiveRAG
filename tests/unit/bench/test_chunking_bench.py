from adaptiverag.ingest.normalize import join_sentences
from adaptiverag.types import Document
from bench.chunking import paired_bootstrap, retention, supporting_spans, top_hits, verdict


def doc(title: str, sentences: list[str]) -> Document:
    text, spans = join_sentences(sentences)
    return Document(f"id-{title}", "t", title, text, spans)


A = doc("A", ["First fact.", "", "Third fact."])
BY_TITLE = {"A": A}


def test_supporting_spans_skip_empty_and_out_of_range_sentences() -> None:
    q = {"supporting_facts": [["A", 0], ["A", 1], ["A", 2], ["A", 9]]}
    assert supporting_spans(q, BY_TITLE) == [("id-A", *A.sentences[0]), ("id-A", *A.sentences[2])]


def test_retention_needs_the_whole_sentence_inside_one_chunk() -> None:
    s0, s2 = A.sentences[0], A.sentences[2]
    spans = [("id-A", *s0), ("id-A", *s2)]
    assert retention(spans, [("id-A", 0, len(A.text))]) == 1.0
    assert retention(spans, [("id-A", s0[0], s0[1])]) == 0.5
    assert retention(spans, [("id-A", s0[0] + 1, s2[1]), ("id-B", 0, 100)]) == 0.5
    assert retention([], [("id-A", 0, 5)]) == 0.0


def test_paired_bootstrap_is_seeded_and_centred_on_the_mean_difference() -> None:
    same = paired_bootstrap([0.5] * 10, [0.5] * 10)
    assert same == (0.0, 0.0, 0.0)
    better = paired_bootstrap([1.0] * 8 + [0.5] * 2, [0.5] * 10)
    assert (
        better[0] == 0.4
        and better[1] > 0
        and better == paired_bootstrap([1.0] * 8 + [0.5] * 2, [0.5] * 10)
    )


def test_verdict_lines() -> None:
    assert verdict("sentence", "sentence", (0.0, 0.0, 0.0)) == "serving now"
    assert verdict("fixed", "sentence", (0.1, 0.02, 0.2)).startswith("beats sentence")
    assert verdict("fixed", "sentence", (-0.1, -0.2, -0.01)).startswith("below sentence")
    assert verdict("semantic", "sentence", (0.05, -0.03, 0.12)).startswith("too close to call")


def test_top_hits_rank_the_pool_exactly() -> None:
    import numpy as np

    from adaptiverag.stores.flat import FlatIndex

    ids = ["d:fixed:0", "d:fixed:1", "d:fixed:2"]
    vecs = np.array([[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]], dtype=np.float32)
    rows = {i: ("d", "Title", f"text {n}", n * 10, n * 10 + 9) for n, i in enumerate(ids)}
    index = FlatIndex()
    index.add(vecs)
    hits = top_hits(index, ids, rows, np.array([0.0, 1.0]), 2)
    assert [(h.chunk_id, h.rank, h.title, h.text) for h in hits] == [
        ("d:fixed:2", 1, "Title", "text 2"),
        ("d:fixed:1", 2, "Title", "text 1"),
    ]
    assert hits[0].score == 1.0 and all(h.source == "vector" for h in hits)
