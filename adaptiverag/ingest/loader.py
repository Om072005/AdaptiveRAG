"""HotpotQA dev (distractor setting): a seeded question sample and its context paragraphs."""

import json
import random
from pathlib import Path
from typing import Any

import httpx

from adaptiverag.config import ROOT
from adaptiverag.ingest.normalize import doc_id, join_sentences
from adaptiverag.types import Document

SOURCE = "hotpotqa-dev"
URL = "http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json"
RAW_PATH = ROOT / "data" / "raw" / "hotpot_dev_distractor_v1.json"


def load_hotpot(n_questions: int, seed: int = 7) -> tuple[list[Document], list[dict[str, Any]]]:
    """Documents = union of the sampled questions' context paragraphs, plus the questions."""
    return from_records(read_raw(), n_questions, seed)


def read_raw(path: Path = RAW_PATH) -> list[dict[str, Any]]:
    """The dev distractor file, downloaded into data/raw/ the first time it is needed."""
    if not path.exists():
        download(URL, path)
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
