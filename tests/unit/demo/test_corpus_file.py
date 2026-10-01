import gzip
from pathlib import Path

import numpy as np
import pytest

from adaptiverag.demo import corpus as dc

DOC = {
    "doc_id": "d1",
    "source": "hotpotqa-dev",
    "title": "Dwell",
    "text": "Dwell is a magazine. It began in 2000.",
    "sentences": [[0, 20], [21, 38]],
}
ROWS = {
    "document": [DOC],
    "chunk": [
        {
            "chunk_id": "d1:sentence:0",
            "doc_id": "d1",
            "ord": 0,
            "start": 0,
            "end": 20,
            "n_words": 4,
        },
        {
            "chunk_id": "d1:sentence:1",
            "doc_id": "d1",
            "ord": 1,
            "start": 21,
            "end": 38,
            "n_words": 4,
            "text": "It began in 2000",
        },
    ],
    "entity": [
        {"canonical_id": "e_a", "canonical_name": "Dwell", "type": "WORK"},
        {
            "canonical_id": "e_b",
            "canonical_name": "2000",
            "type": "DATE",
            "vector": dc.b64_vector(np.ones(3)),
        },
    ],
    "alias": [{"surface_form": "Dwell", "canonical_id": "e_a", "confidence": 1.0}],
    "relation": [
        {
            "rel_id": "r1",
            "subject_id": "e_a",
            "predicate": "launched_in",
            "object_id": "e_b",
            "chunk_id": "d1:sentence:1",
            "doc_id": "d1",
            "evidence_start": 21,
            "evidence_end": 38,
            "extraction_confidence": 0.9,
        },
    ],
}


def corpus() -> dc.Corpus:
    meta = {
        "format": 1,
        "strategy": "sentence",
        "counts": {k: len(v) for k, v in ROWS.items()},
        "content": dc.content_hash(ROWS),
    }
    return dc.Corpus(meta, ROWS)


def test_the_file_reads_back_as_written_and_the_same_rows_give_the_same_bytes(
    tmp_path: Path,
) -> None:
    a, b = tmp_path / "a.jsonl.gz", tmp_path / "b.jsonl.gz"
    dc.write_corpus(a, corpus())
    dc.write_corpus(b, corpus())
    assert a.read_bytes() == b.read_bytes()
    back = dc.read_corpus(a)
    assert back.meta == corpus().meta and back.rows == ROWS


def test_a_file_whose_rows_do_not_match_its_counts_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl.gz"
    dc.write_corpus(path, corpus())
    lines = gzip.decompress(path.read_bytes()).decode().splitlines()
    path.write_bytes(gzip.compress(("\n".join(lines[:-1]) + "\n").encode()))  # drop the relation
    with pytest.raises(ValueError, match="do not match the meta line"):
        dc.read_corpus(path)


def test_texts_to_embed_follow_the_build_recipe() -> None:
    texts = dc.embed_texts(ROWS)
    assert texts["chunk"] == [
        "Dwell is a magazine.",
        "It began in 2000",
    ]  # a slice, or the stored text
    assert texts["entity"] == ["Dwell", "2000"]
    assert texts["relation"] == ["Dwell launched in 2000"]


def test_copy_rows_carry_the_chunk_text_and_strategy() -> None:
    rows = list(dc.copy_values("chunk", corpus()))
    assert rows[0] == ("d1:sentence:0", "d1", "sentence", 0, 0, 20, "Dwell is a magazine.", 4)
    assert list(dc.copy_values("document", corpus()))[0][4] == "[[0, 20], [21, 38]]"


def test_a_shipped_vector_round_trips() -> None:
    assert dc.vector_b64(ROWS["entity"][1]["vector"]).tolist() == [1.0, 1.0, 1.0]


def test_the_repo_corpus_file_is_complete() -> None:
    data = dc.read_corpus()
    assert data.meta["strategy"] == "sentence" and data.meta["content"] == dc.content_hash(
        data.rows
    )
    assert all(data.meta["counts"][k] > 0 for k in dc.KINDS)
