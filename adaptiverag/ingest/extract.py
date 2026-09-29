"""Triple extraction: the prompt, the JSON schema the model answers in, and the response parser."""

import json
import re
from collections import Counter
from dataclasses import asdict
from typing import Any

from adaptiverag import llm
from adaptiverag.config import ingest_cfg
from adaptiverag.ingest.validate import validate
from adaptiverag.types import Chunk, LLMResult, Triple

# the closed list, same as the entities.type check in db/migrations/0001_init.sql
ENTITY_TYPES = ("PERSON", "ORG", "PLACE", "WORK", "EVENT", "DATE", "OTHER")

TRIPLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["triples"],
    "properties": {
        "triples": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "chunk",
                    "subject",
                    "subject_type",
                    "predicate",
                    "object",
                    "object_type",
                    "evidence",
                    "confidence",
                ],
                "properties": {
                    "chunk": {"type": "integer", "minimum": 1},
                    "subject": {"type": "string"},
                    "subject_type": {"type": "string", "enum": list(ENTITY_TYPES)},
                    "predicate": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                    "object": {"type": "string"},
                    "object_type": {"type": "string", "enum": list(ENTITY_TYPES)},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}
ITEM_SCHEMA: dict[str, Any] = TRIPLE_SCHEMA["properties"]["triples"]["items"]

SYSTEM_PROMPT = f"""You extract facts from short Wikipedia passages as \
(subject, predicate, object) triples for a knowledge graph. Treat every passage on its own and \
list every fact in it that links two named things; most passages state several.

Rules:
1. Use only facts the passage states. Add no outside knowledge.
2. subject and object are names or dates copied exactly as written in the passage, never a \
description such as "an American actor". If the passage says "he", "she", "it" or "the school", \
use the name it refers to only when that name is written in the same passage; otherwise skip \
the fact.
3. subject_type and object_type come from this closed list: {", ".join(ENTITY_TYPES)}.
4. predicate is a short verb phrase in lower snake case, in the active voice from subject to \
object: (Tim Burton, directed, Ed Wood), not (Ed Wood, directed_by, Tim Burton).
5. evidence is the shortest exact quote from the passage that states the fact.
6. confidence is a number from 0 to 1: 1 when the passage says it in so many words, lower when \
you had to infer it.
7. chunk is the number in brackets of the passage the fact comes from.
8. Answer with JSON only: one object that matches the schema below. \
Use {{"triples": []}} when no passage states a fact.

Schema:
{json.dumps(TRIPLE_SCHEMA)}"""

NOT_SNAKE = re.compile(r"[^a-z0-9]+")


def build_messages(chunks: list[Chunk]) -> list[dict[str, str]]:
    """System prompt with the schema, then the chunks numbered [1]..[n] in one user message."""
    blocks = "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(chunks, 1))
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Passages:\n\n{blocks}"},
    ]


def snake_case(predicate: str) -> str:
    """'Born In' -> 'born_in'. The graph stores predicates in lower snake case."""
    return NOT_SNAKE.sub("_", predicate.lower()).strip("_")


def evidence_span(evidence: str, chunk: Chunk) -> tuple[int, int]:
    """Offsets of the quoted evidence in documents.text; the whole chunk if the quote is missing."""
    quote = evidence.strip()
    found = re.search(re.escape(quote), chunk.text, re.IGNORECASE) if quote else None
    if found is None:
        return chunk.start, chunk.end
    return chunk.start + found.start(), chunk.start + found.end()


def passage(item: Any, chunks: list[Chunk]) -> Chunk | None:
    """The chunk a model item points at, or None if its chunk number is not one we sent."""
    n = item.get("chunk") if isinstance(item, dict) else None
    if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(chunks):
        return chunks[n - 1]
    return None


def schema_problem(item: Any, chunks: list[Chunk]) -> str | None:
    """Why one model item breaks the triple schema, or None when it fits."""
    if not isinstance(item, dict):
        return "not an object"
    missing = [f for f in ITEM_SCHEMA["required"] if f not in item]
    if missing:
        return "missing " + ", ".join(missing)
    if passage(item, chunks) is None:
        return "chunk is not a passage number"
    for name in ("subject", "predicate", "object", "evidence"):
        if not isinstance(item[name], str):
            return f"{name} is not a string"
    for name in ("subject_type", "object_type"):
        if item[name] not in ENTITY_TYPES:
            return f"{name} is not in the entity type list"
    conf = item["confidence"]
    if not isinstance(conf, int | float) or isinstance(conf, bool) or not 0 <= conf <= 1:
        return "confidence is not a number in 0..1"
    return None


def parse_response(text: str, chunks: list[Chunk]) -> tuple[list[Triple], list[dict[str, Any]]]:
    """Model JSON -> (triples, bad_json rejects). Items that break the schema are not repaired."""
    try:
        items = json.loads(text)["triples"]
        if not isinstance(items, list):
            raise TypeError("triples is not a list")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raw = {"response": text, "chunk_ids": [c.chunk_id for c in chunks], "problem": str(e)}
        return [], [{"chunk_id": None, "raw": raw, "reason": "bad_json"}]

    triples: list[Triple] = []
    rejects: list[dict[str, Any]] = []
    for item in items:
        chunk = passage(item, chunks)
        problem = schema_problem(item, chunks)
        if problem or chunk is None:
            chunk_id = chunk.chunk_id if chunk else None
            bad = {"item": item, "problem": problem}
            rejects.append({"chunk_id": chunk_id, "raw": bad, "reason": "bad_json"})
            continue
        start, end = evidence_span(item["evidence"], chunk)
        triples.append(
            Triple(
                subject=item["subject"].strip(),
                subject_type=item["subject_type"],
                predicate=snake_case(item["predicate"]),
                object=item["object"].strip(),
                object_type=item["object_type"],
                chunk_id=chunk.chunk_id,
                evidence_start=start,
                evidence_end=end,
                confidence=float(item["confidence"]),
            )
        )
    return triples, rejects


def check_offsets(chunks: list[Chunk], doc_text: dict[str, str]) -> None:
    """Evidence offsets are stored against documents.text; a stale chunk row stops the run."""
    for c in chunks:
        if doc_text[c.doc_id][c.start : c.end] != c.text:
            raise ValueError(f"{c.chunk_id} does not match documents.text at {c.start}:{c.end}")


def screen(
    triples: list[Triple], chunks: dict[str, Chunk], min_confidence: float
) -> tuple[list[Triple], list[dict[str, Any]]]:
    """Source validation first, then the confidence bar; every reject keeps its reason."""
    kept: list[Triple] = []
    rejects: list[dict[str, Any]] = []
    for t in triples:
        reason = validate(t, chunks[t.chunk_id].text)
        if reason is None and t.confidence < min_confidence:
            reason = "low_confidence"
        if reason is None:
            kept.append(t)
        else:
            rejects.append({"chunk_id": t.chunk_id, "raw": asdict(t), "reason": reason})
    return kept, rejects


def extract_batches(
    chunks: list[Chunk], doc_text: dict[str, str]
) -> tuple[list[Triple], list[dict[str, Any]], list[LLMResult]]:
    """extract_triples plus the calls it made, for the run summary.

    Batches follow the order of chunks, so the same chunk list hits the cache on a rerun.
    """
    cfg = ingest_cfg()["extract"]
    check_offsets(chunks, doc_text)
    by_id = {c.chunk_id: c for c in chunks}
    size = int(cfg["chunks_per_call"])
    kept: list[Triple] = []
    rejects: list[dict[str, Any]] = []
    calls: list[LLMResult] = []
    for i in range(0, len(chunks), size):
        batch = chunks[i : i + size]
        result = llm.chat(
            "extract",
            build_messages(batch),
            json_mode=True,
            temperature=0.0,
            max_tokens=int(cfg["max_tokens"]),
        )
        calls.append(result)
        triples, bad = parse_response(result.text, batch)
        ok, rejected = screen(triples, by_id, float(cfg["min_confidence"]))
        kept += ok
        rejects += bad + rejected
    return kept, rejects, calls


def extract_triples(
    chunks: list[Chunk], doc_text: dict[str, str]
) -> tuple[list[Triple], list[dict[str, Any]]]:
    """(kept, rejects); 4 chunks per call, role 'extract', json mode."""
    kept, rejects, _ = extract_batches(chunks, doc_text)
    return kept, rejects


def summarize(
    chunks: list[Chunk], kept: list[Triple], rejects: list[dict[str, Any]], calls: list[LLMResult]
) -> dict[str, Any]:
    """Run summary. reject_rate = rejected triples over all triples the model returned; a whole
    response that was not JSON has no triples to count, so it is reported on its own line."""
    by_id = {c.chunk_id: c for c in chunks}
    bad_responses = sum(1 for r in rejects if "response" in r["raw"])
    rejected_triples = len(rejects) - bad_responses
    returned = len(kept) + rejected_triples
    whole_chunk = sum(
        1
        for t in kept
        if (t.evidence_start, t.evidence_end) == (by_id[t.chunk_id].start, by_id[t.chunk_id].end)
    )
    return {
        "chunks": len(chunks),
        "chunks_with_triples": len({t.chunk_id for t in kept}),
        "calls": len(calls),
        "calls_cached": sum(c.cached for c in calls),
        "tokens_in": sum(c.tokens_in for c in calls),
        "tokens_out": sum(c.tokens_out for c in calls),
        "cost_usd_list_price": round(sum(c.cost_usd for c in calls), 8),
        "cost_usd_this_run": round(sum(c.cost_usd for c in calls if not c.cached), 8),
        "triples_returned": returned,
        "kept": len(kept),
        "rejected": rejected_triples,
        "reject_rate": round(rejected_triples / returned, 4) if returned else None,
        "rejects_by_reason": dict(sorted(Counter(r["reason"] for r in rejects).items())),
        "bad_responses": bad_responses,
        "evidence_not_found": whole_chunk,
    }
