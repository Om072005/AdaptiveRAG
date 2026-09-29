"""HotpotQA dev (distractor setting): a seeded question sample and its context paragraphs."""

import json
import random
import time
from pathlib import Path
from typing import Any

import httpx

from adaptiverag.config import ROOT
from adaptiverag.ingest.normalize import doc_id, join_sentences
from adaptiverag.types import Document

SOURCE = "hotpotqa-dev"
URL = "http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json"
# The same 7,405 questions published as a Hugging Face dataset, used when the official host is down.
MIRROR_URL = "https://datasets-server.huggingface.co/rows"
MIRROR_PARAMS: dict[str, str | int] = {
    "dataset": "hotpotqa/hotpot_qa",
    "config": "distractor",
    "split": "validation",
}
RAW_PATH = ROOT / "data" / "raw" / "hotpot_dev_distractor_v1.json"
CORPUS_DIR = ROOT / "data" / "corpus"
CORPUS_QUESTIONS = {"mini": 30, "full": 300}  # corpus sizes fixed by the contract (section 4)


def load_hotpot(n_questions: int, seed: int = 7) -> tuple[list[Document], list[dict[str, Any]]]:
    """Documents = union of the sampled questions' context paragraphs, plus the questions."""
    return from_records(read_raw(), n_questions, seed)


def read_raw(path: Path = RAW_PATH) -> list[dict[str, Any]]:
    """The dev distractor file, downloaded into data/raw/ the first time it is needed."""
    if not path.exists():
        try:
            download(URL, path)
        except httpx.TransportError:
            print(f"{URL} did not answer, writing the Hugging Face copy instead")
            download_mirror(path)
    records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return records


def download(url: str, path: Path) -> None:
    """Stream to a .part file and rename, so a broken download is never read as the dataset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as response:
        response.raise_for_status()
        with part.open("wb") as f:
            for block in response.iter_bytes():
                f.write(block)
    part.replace(path)


def download_mirror(path: Path, page: int = 100) -> None:
    """Page through the Hugging Face copy in order and write it in the original file layout."""
    records: list[dict[str, Any]] = []
    total = None
    with httpx.Client(timeout=60) as client:
        while total is None or len(records) < total:
            body = mirror_page(client, len(records), page)
            # the seeded sample depends on file order, so every page must start where the last ended
            if not body["rows"] or body["rows"][0]["row_idx"] != len(records):
                raise ValueError(f"mirror page at offset {len(records)} is empty or out of order")
            total = body["num_rows_total"]
            records += [from_mirror_row(r["row"]) for r in body["rows"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    part.replace(path)


def mirror_page(client: httpx.Client, offset: int, length: int) -> dict[str, Any]:
    """One page of rows; waits out a 429 up to 5 times before giving up."""
    params = MIRROR_PARAMS | {"offset": offset, "length": length}
    for attempt in range(5):
        response = client.get(MIRROR_URL, params=params)
        if response.status_code != 429:
            break
        time.sleep(float(response.headers.get("retry-after", 10 * 2**attempt)))
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


def from_mirror_row(row: dict[str, Any]) -> dict[str, Any]:
    """One Hugging Face row back in the original record layout."""
    context, facts = row["context"], row["supporting_facts"]
    return {
        "_id": row["id"],
        "answer": row["answer"],
        "question": row["question"],
        "supporting_facts": [list(f) for f in zip(facts["title"], facts["sent_id"], strict=True)],
        "context": [list(p) for p in zip(context["title"], context["sentences"], strict=True)],
        "type": row["type"],
        "level": row["level"],
    }


def sample(records: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    """First n of a seeded shuffle, so a smaller sample is always a prefix of a larger one."""
    order = list(range(len(records)))
    random.Random(seed).shuffle(order)
    return [records[i] for i in order[:n]]


def from_records(
    records: list[dict[str, Any]], n_questions: int, seed: int = 7
) -> tuple[list[Document], list[dict[str, Any]]]:
    """Sample questions and build one Document per unique context title (first seen wins)."""
    if not 0 < n_questions <= len(records):
        raise ValueError(f"n_questions must be in 1..{len(records)}, got {n_questions}")
    docs: dict[str, Document] = {}
    questions: list[dict[str, Any]] = []
    for r in sample(records, n_questions, seed):
        for title, sentences in r["context"]:
            if title not in docs:
                text, spans = join_sentences(sentences)
                docs[title] = Document(doc_id(SOURCE, title), SOURCE, title, text, spans)
        questions.append(
            {
                "id": r["_id"],
                "question": r["question"],
                "answer": r["answer"],
                "type": r["type"],
                "level": r["level"],
                "supporting_facts": [[title, i] for title, i in r["supporting_facts"]],
                "titles": [title for title, _ in r["context"]],
            }
        )
    return list(docs.values()), questions


def manifest(questions: list[dict[str, Any]], docs: list[Document], seed: int) -> dict[str, Any]:
    """The data/corpus/<name>.json content for a sample."""
    return {
        "seed": seed,
        "source": "hotpotqa-dev-distractor",
        "question_ids": [q["id"] for q in questions],
        "doc_ids": [d.doc_id for d in docs],
    }


def corpus(
    name: str, seed: int = 7, corpus_dir: Path = CORPUS_DIR
) -> tuple[list[Document], list[dict[str, Any]]]:
    """A named sample; writes data/corpus/<name>.json once and checks it on every later call."""
    docs, questions = load_hotpot(CORPUS_QUESTIONS[name], seed)
    built = manifest(questions, docs, seed)
    path = corpus_dir / f"{name}.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != built:
            raise SystemExit(f"{path} does not match the {name} sample of the raw file")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(built, indent=1) + "\n", encoding="utf-8")
    return docs, questions


def manifest_doc_ids(name: str, corpus_dir: Path = CORPUS_DIR) -> list[str]:
    """doc_ids of a committed corpus manifest; needs no raw file."""
    path = corpus_dir / f"{name}.json"
    return list(json.loads(path.read_text(encoding="utf-8"))["doc_ids"])
