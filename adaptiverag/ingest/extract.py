"""Triple extraction: the prompt, the JSON schema the model answers in, and the response parser."""

import json
import re
from typing import Any

from adaptiverag.types import Chunk, Triple

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
(subject, predicate, object) triples for a knowledge graph.

Rules:
1. Use only facts the passage states. Add no outside knowledge.
2. subject and object are names copied exactly as written in the passage. If the passage says \
"he", "she" or "it", use the name it refers to only when that name is written in the same passage; \
otherwise skip the fact.
3. subject_type and object_type come from this closed list: {", ".join(ENTITY_TYPES)}.
4. predicate is a short verb phrase in lower snake case, in the active voice from subject to \
object: (Tim Burton, directed, Ed Wood), not (Ed Wood, directed_by, Tim Burton).
5. evidence is the shortest exact quote from the passage that states the fact.
6. confidence is a number from 0 to 1: how directly the passage states the fact.
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


def extract_triples(
    chunks: list[Chunk], doc_text: dict[str, str]
) -> tuple[list[Triple], list[dict[str, Any]]]:
    """(kept, rejects); 4 chunks per call, role 'extract', json mode."""
    raise NotImplementedError
