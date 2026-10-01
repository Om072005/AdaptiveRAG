"""The demo corpus file: everything the served path reads, as text, in one gzip of JSON lines.

Export (lead, from Neon main) writes data/demo/corpus.jsonl.gz: documents, the serving strategy's
chunks, entities, aliases and relations. Vectors are left out, because they would weigh ~55 MB;
load embeds the same texts with the same local model instead. Export re-embeds every text on this
machine first and ships the stored vector only for the few rows that do not come out the same
(cosine below SAME_VECTOR), so a load reproduces Neon main's vectors either way."""

import base64
import gzip
import hashlib
import json
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import psycopg

from adaptiverag import llm
from adaptiverag.config import ROOT, models, router_cfg
from adaptiverag.ingest.resolve import relation_texts

CORPUS_FILE = ROOT / "data" / "demo" / "corpus.jsonl.gz"
SAME_VECTOR = 0.9999  # cosine at or above which a local re-embedding counts as the stored vector
EMBED_BATCH = 100
KINDS = ("document", "chunk", "entity", "alias", "relation")

Progress = Callable[[str, int, int], None]  # (what, done, total)


@dataclass(frozen=True)
class Corpus:
    meta: dict[str, Any]
    rows: dict[str, list[dict[str, Any]]]  # kind -> rows, in file order


def b64_vector(vec: np.ndarray) -> str:
    return base64.b64encode(np.asarray(vec, dtype=np.float32).tobytes()).decode()


def vector_b64(text: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(text), dtype=np.float32)


def write_corpus(path: Path, corpus: Corpus) -> None:
    """One JSON object per line: the meta line, then every row with its kind. mtime 0 and no file
    name in the header keep the gzip bytes the same for the same rows."""
    lines = [json.dumps({"kind": "meta", **corpus.meta}, ensure_ascii=False)]
    for kind in KINDS:
        lines += [json.dumps({"kind": kind, **r}, ensure_ascii=False) for r in corpus.rows[kind]]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write(("\n".join(lines) + "\n").encode("utf-8"))


def read_corpus(path: Path = CORPUS_FILE) -> Corpus:
    meta: dict[str, Any] = {}
    rows: dict[str, list[dict[str, Any]]] = {k: [] for k in KINDS}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            kind = item.pop("kind")
            if kind == "meta":
                meta = item
            elif kind in rows:
                rows[kind].append(item)
            else:
                raise ValueError(f"{path}: unknown row kind {kind!r}")
    counts = {k: len(v) for k, v in rows.items()}
    if counts != meta.get("counts"):
        raise ValueError(f"{path}: rows {counts} do not match the meta line {meta.get('counts')}")
    return Corpus(meta, rows)


def content_hash(rows: dict[str, list[dict[str, Any]]]) -> str:
    """sha256 over the rows, so a load can say which export it holds."""
    digest = hashlib.sha256()
    for kind in KINDS:
        for r in rows[kind]:
            digest.update(json.dumps(r, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return digest.hexdigest()[:16]


# --- what gets embedded -------------------------------------------------------------------


def chunk_text(chunk: dict[str, Any], docs: dict[str, dict[str, Any]]) -> str:
    """A chunk's text: its slice of the document, unless the export had to store it."""
    if "text" in chunk:
        return str(chunk["text"])
    return str(docs[chunk["doc_id"]]["text"][chunk["start"] : chunk["end"]])


def embed_texts(corpus_rows: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    """The texts load embeds, per kind with a vector: chunk text, entity name, and the relation
    as 'subject predicate object' (ingest.resolve.relation_texts, the build's own recipe)."""
    docs = {d["doc_id"]: d for d in corpus_rows["document"]}
    return {
        "chunk": [chunk_text(c, docs) for c in corpus_rows["chunk"]],
        "entity": [e["canonical_name"] for e in corpus_rows["entity"]],
        "relation": relation_texts(corpus_rows["entity"], corpus_rows["relation"]),
    }


def batched(items: list[str], size: int) -> Iterator[tuple[int, list[str]]]:
    for start in range(0, len(items), size):
        yield start, items[start : start + size]


def embed_all(texts: list[str], what: str, progress: Progress | None) -> np.ndarray:
    """Embed without the cache (a fresh vector from the local model), in batches."""
    out = np.zeros((len(texts), models()["embed"].dims or 768), dtype=np.float32)
    with llm.fresh():
        for start, batch in batched(texts, EMBED_BATCH):
            out[start : start + len(batch)] = llm.embed(batch)
            if progress:
                progress(what, start + len(batch), len(texts))
    return out


# --- export (from the team database) -------------------------------------------------------

EXPORT_QUERIES = {
    "document": "select doc_id, source, title, text, sentences from documents "
    "where doc_id in (select doc_id from chunks where strategy = %(s)s) order by doc_id",
    "chunk": "select chunk_id, doc_id, ord, start_offset, end_offset, text, n_words, embedding "
    "from chunks where strategy = %(s)s order by chunk_id",
    "entity": "select canonical_id, canonical_name, type, embedding from entities "
    "order by canonical_id",
    "alias": "select surface_form, canonical_id, confidence from aliases "
    "order by surface_form, canonical_id",
    # relations must cite a chunk the file holds (relations.chunk_id references chunks)
    "relation": "select rel_id, subject_id, predicate, object_id, chunk_id, doc_id, "
    "evidence_start, evidence_end, extraction_confidence, embedding from relations "
    "where chunk_id in (select chunk_id from chunks where strategy = %(s)s) order by rel_id",
}


def export_rows(
    c: psycopg.Connection[Any], strategy: str
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, np.ndarray]]:
    """Rows as the file stores them, and the stored vectors per kind (row order)."""
    rows: dict[str, list[dict[str, Any]]] = {}
    stored: dict[str, np.ndarray] = {}
    for kind, query in EXPORT_QUERIES.items():
        cur = c.execute(query, {"s": strategy})
        names = [d.name for d in cur.description or []]
        records = [dict(zip(names, r, strict=True)) for r in cur.fetchall()]
        if "embedding" in names:
            unembedded = [r for r in records if r["embedding"] is None]
            if unembedded:
                raise ValueError(
                    f"{len(unembedded)} {kind} rows have no embedding; embed them first"
                )
            stored[kind] = np.array([np.asarray(r.pop("embedding").to_numpy()) for r in records])
        rows[kind] = records
    docs = {d["doc_id"]: d for d in rows["document"]}
    for ch in rows["chunk"]:
        ch["start"], ch["end"] = ch.pop("start_offset"), ch.pop("end_offset")
        text = ch.pop("text")
        if docs[ch["doc_id"]]["text"][ch["start"] : ch["end"]] != text:
            ch["text"] = text  # only when the slice would not give it back
    return rows, stored


def cosines(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.asarray(
        np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
    )


def pin_mismatches(
    rows: dict[str, list[dict[str, Any]]], stored: dict[str, np.ndarray], progress: Progress | None
) -> dict[str, int]:
    """Re-embed every text here; rows whose fresh vector differs keep the stored one in the file.
    Returns how many rows per kind carry a vector."""
    texts = embed_texts(rows)
    pinned: dict[str, int] = {}
    for kind, items in texts.items():
        fresh = embed_all(items, kind, progress)
        differ = np.flatnonzero(cosines(fresh, stored[kind]) < SAME_VECTOR)
        for i in differ:
            rows[kind][int(i)]["vector"] = b64_vector(stored[kind][int(i)])
        pinned[kind] = int(len(differ))
    return pinned


def export(c: psycopg.Connection[Any], git_sha: str, progress: Progress | None = None) -> Corpus:
    strategy = str(router_cfg()["serving"]["chunk_strategy"])
    rows, stored = export_rows(c, strategy)
    pinned = pin_mismatches(rows, stored, progress)
    meta = {
        "format": 1,
        "strategy": strategy,
        "embed_model": models()["embed"].model,
        "exported_at_sha": git_sha,
        "counts": {k: len(v) for k, v in rows.items()},
        "vectors_in_file": pinned,
        "content": content_hash(rows),
    }
    return Corpus(meta, rows)


# --- load (into the demo database) ---------------------------------------------------------

COPY = {
    "document": ("documents", ("doc_id", "source", "title", "text", "sentences")),
    "chunk": (
        "chunks",
        ("chunk_id", "doc_id", "strategy", "ord", "start_offset", "end_offset", "text", "n_words"),
    ),
    "entity": ("entities", ("canonical_id", "canonical_name", "type")),
    "alias": ("aliases", ("surface_form", "canonical_id", "confidence")),
    "relation": (
        "relations",
        (
            "rel_id",
            "subject_id",
            "predicate",
            "object_id",
            "chunk_id",
            "doc_id",
            "evidence_start",
            "evidence_end",
            "extraction_confidence",
        ),
    ),
}
VECTOR_TABLE = {
    "chunk": ("chunks", "chunk_id"),
    "entity": ("entities", "canonical_id"),
    "relation": ("relations", "rel_id"),
}


def copy_values(kind: str, corpus: Corpus) -> Iterable[tuple[Any, ...]]:
    docs = {d["doc_id"]: d for d in corpus.rows["document"]}
    strategy = corpus.meta["strategy"]
    for r in corpus.rows[kind]:
        if kind == "document":
            yield (r["doc_id"], r["source"], r["title"], r["text"], json.dumps(r["sentences"]))
        elif kind == "chunk":
            text = chunk_text(r, docs)
            yield (
                r["chunk_id"],
                r["doc_id"],
                strategy,
                r["ord"],
                r["start"],
                r["end"],
                text,
                r["n_words"],
            )
        else:
            yield tuple(r[col] for col in COPY[kind][1])


def table_counts(c: psycopg.Connection[Any]) -> dict[str, int]:
    out = {}
    for kind, (table, _) in COPY.items():
        row = c.execute(f"select count(*) from {table}").fetchone()  # noqa: S608 (fixed names)
        out[kind] = int(row[0]) if row else 0
    return out


def missing_vectors(c: psycopg.Connection[Any]) -> dict[str, int]:
    out = {}
    for kind, (table, _) in VECTOR_TABLE.items():
        row = c.execute(f"select count(*) from {table} where embedding is null").fetchone()  # noqa: S608
        out[kind] = int(row[0]) if row else 0
    return out


def load_rows(c: psycopg.Connection[Any], corpus: Corpus) -> None:
    """Copy every row in one transaction. Refuses a database that already holds other rows."""
    have = table_counts(c)
    if any(have.values()):
        if have == corpus.meta["counts"]:
            return  # loaded before; embedding below resumes where it stopped
        raise RuntimeError(f"the database already holds other rows {have}; use an empty one")
    with c.transaction():
        for kind, (table, cols) in COPY.items():
            with c.cursor().copy(f"copy {table} ({', '.join(cols)}) from stdin") as cp:
                for values in copy_values(kind, corpus):
                    cp.write_row(values)


def store_vectors(c: psycopg.Connection[Any], kind: str, ids: list[str], vecs: np.ndarray) -> None:
    table, key = VECTOR_TABLE[kind]
    with c.transaction(), c.cursor() as cur:
        cur.executemany(
            f"update {table} set embedding = %s where {key} = %s",  # noqa: S608 (fixed names)
            list(zip(vecs, ids, strict=True)),
        )


def embed_missing(c: psycopg.Connection[Any], corpus: Corpus, progress: Progress | None) -> None:
    """Fill every null embedding: from the file when it carries the vector, else embedded here.
    Each batch commits, so a stopped load resumes at the first row still missing a vector."""
    texts = embed_texts(corpus.rows)
    for kind, (table, key) in VECTOR_TABLE.items():
        todo = {r[0] for r in c.execute(f"select {key} from {table} where embedding is null")}  # noqa: S608
        rows = [(i, r) for i, r in enumerate(corpus.rows[kind]) if r[key] in todo]
        given = [(r[key], vector_b64(r["vector"])) for _, r in rows if "vector" in r]
        if given:
            store_vectors(c, kind, [g[0] for g in given], np.array([g[1] for g in given]))
        need = [(r[key], texts[kind][i]) for i, r in rows if "vector" not in r]
        done = len(corpus.rows[kind]) - len(need)
        for start, batch in batched([t for _, t in need], EMBED_BATCH):
            ids = [k for k, _ in need[start : start + len(batch)]]
            with llm.fresh():  # 18k vectors would only bloat the local cache
                vecs = llm.embed(batch)
            store_vectors(c, kind, ids, vecs)
            if progress:
                progress(kind, done + start + len(batch), len(corpus.rows[kind]))
