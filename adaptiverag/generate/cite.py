"""Parse the model's answer and bind its [n] markers to the context blocks they point at."""

import re

from adaptiverag.generate.prompts import NOT_ENOUGH
from adaptiverag.types import Citation, Hit, Retrieved

SNIPPET_CHARS = 600
MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
ANSWER_LINE = re.compile(r"^\W*answer\W*:\s*(.*)$", re.IGNORECASE)


def marker_numbers(text: str) -> list[int]:
    """Every n in [n] or [n, m] markers, in order of appearance."""
    return [int(n) for group in MARKER.findall(text) for n in group.split(",")]


def invalid_markers(raw: str, n_blocks: int) -> int:
    """How many markers point at a block that does not exist (stored as detail.citation_errors)."""
    return sum(1 for n in marker_numbers(raw) if not 1 <= n <= n_blocks)


def split_answer(raw: str) -> tuple[str, str]:
    """(short answer, explanation) from 'Answer: <span>' followed by the explanation."""
    lines = [line for line in raw.strip().splitlines() if line.strip()]
    for i, line in enumerate(lines):
        m = ANSWER_LINE.match(line.strip())
        if m:
            return m.group(1).strip(), " ".join(lines[i + 1 :]).strip()
    # no answer line: treat the first line as the answer, never guess beyond what was written
    return (lines[0].strip(), " ".join(lines[1:]).strip()) if lines else (NOT_ENOUGH, "")


def clean_short(short: str) -> str:
    short = MARKER.sub("", short).strip().strip("*_\"'").strip()
    return short.rstrip(".").strip()


def bind_citations(raw: str, retrieved: Retrieved) -> tuple[str, str, list[Citation]]:
    """Parse the model output into (short, text, citations), dropping out of range markers."""
    hits: list[Hit] = sorted(retrieved.hits, key=lambda h: h.rank)
    short_raw, explanation = split_answer(raw)
    short = clean_short(short_raw)
    if short.lower().startswith(NOT_ENOUGH) or not hits:
        return NOT_ENOUGH, NOT_ENOUGH, []

    def keep_valid(m: re.Match[str]) -> str:
        valid = [n for n in (int(x) for x in m.group(1).split(",")) if 1 <= n <= len(hits)]
        return "[" + ", ".join(map(str, valid)) + "]" if valid else ""

    explanation = re.sub(r"\s+([.,;])", r"\1", MARKER.sub(keep_valid, explanation)).strip()
    text = f"{short}. {explanation}" if explanation else short
    citations: list[Citation] = []
    for n in dict.fromkeys(marker_numbers(explanation)):
        h = hits[n - 1]
        citations.append(Citation(n, h.chunk_id, h.doc_id, h.title, h.text[:SNIPPET_CHARS]))
    return short, text, citations
