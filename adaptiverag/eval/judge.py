import json
import re
from typing import Any

from adaptiverag import llm
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Answer, Retrieved

SCORES = ("faithfulness", "relevance", "completeness")
RETRY = (
    "Your reply was not valid. Reply with one JSON object only, with integer scores from 1 to 5 "
    'for "faithfulness", "relevance" and "completeness" and a short "rationale".'
)


class JudgeFailed(Exception):
    """The judge gave no valid scores after one retry; stored as a failure, never as a score."""


# Kept word for word in docs/eval-protocol.md; a test fails if the two drift apart.
RUBRIC = """Score each metric from 1 to 5.

faithfulness: is every claim in the answer supported by the context?
5 every claim is stated in the context
4 all claims supported, one needs a small inference the context clearly allows
3 the main answer is supported, but one side claim is not in the context
2 the main answer is not supported by the context, some side claims are
1 the answer contradicts the context or is not grounded in it at all
If the answer says "not enough context", score 5 when the context really lacks the answer, else 1.

relevance: are the retrieved context blocks actually about the question?
5 every block is about the question's entities and what it asks
4 most blocks are on topic, one or two are off topic
3 about half the blocks are on topic
2 one block is on topic, the rest are not
1 no block is about the question

completeness: does the answer cover every part of the question?
5 every part is answered (both sides of a comparison, every hop of a chain)
4 every part is answered, one only vaguely
3 one part of a multi part question is missing
2 most parts are missing
1 the answer does not address the question
A single part question answered fully scores 5, whether or not the answer is correct."""

PROMPT = """You grade one answer from a question answering system. Judge only what is written below.
Do not use outside knowledge to decide whether a claim is true: a claim counts as supported only
if the context states it.

{rubric}

Reply with JSON only:
{{"faithfulness": 1-5, "relevance": 1-5, "completeness": 1-5, "rationale": "one or two sentences"}}

Question: {question}

Context:
{context}

Answer:
{answer}"""


def context_blocks(retrieved: Retrieved) -> str:
    """Hits as numbered blocks in rank order, plus graph facts, as the generator saw them."""
    hits = sorted(retrieved.hits, key=lambda h: h.rank)
    block = {h.chunk_id: n for n, h in enumerate(hits, start=1)}
    lines = [f"[{n}] {h.title}: {h.text}" for n, h in enumerate(hits, start=1)]
    facts = [
        f"({e.subject_name}) -[{e.predicate}]-> ({e.object_name}) [{block[e.chunk_id]}]"
        for p in retrieved.paths
        for e in p.edges
        if e.chunk_id in block
    ]
    if facts:
        lines += ["Graph facts:", *dict.fromkeys(facts)]
    return "\n".join(lines) if lines else "(no context was retrieved)"


def build_messages(question: str, answer: Answer, retrieved: Retrieved) -> list[dict[str, str]]:
    """The judge prompt: rubric, question, numbered context and the answer text with markers."""
    content = PROMPT.format(
        rubric=RUBRIC, question=question, context=context_blocks(retrieved), answer=answer.text
    )
    return [{"role": "user", "content": content}]


THOUGHT = re.compile(r"<thought>.*?</thought>", re.DOTALL)
FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def json_payload(raw: str) -> str:
    """The JSON part of a reply: without a leading thought block and outside a code fence."""
    text = THOUGHT.sub("", raw).strip()
    fenced = FENCE.search(text)
    return fenced.group(1) if fenced else text


def parse_scores(raw: str) -> dict[str, Any] | str:
    """Scores mapped from 1..5 to 0..1 plus the rationale, or why the reply is invalid."""
    try:
        data = json.loads(json_payload(raw))
    except ValueError:
        return "not json"
    if not isinstance(data, dict):
        return "not a json object"
    out: dict[str, Any] = {}
    for name in SCORES:
        s = data.get(name)
        if type(s) is not int or not 1 <= s <= 5:
            return f"{name} is not an integer from 1 to 5"
        out[name] = (s - 1) / 4
    out["rationale"] = str(data.get("rationale", "")).strip()
    return out


def judge(question: str, answer: Answer, retrieved: Retrieved, trace: Trace) -> dict[str, Any]:
    """{faithfulness, relevance, completeness in 0..1, rationale}. Raises JudgeFailed."""
    messages = build_messages(question, answer, retrieved)
    first = llm.chat("judge", messages, json_mode=True, trace=trace, max_tokens=1024)
    got = parse_scores(first.text)
    calls = [first]
    if isinstance(got, str):
        # a changed request, since the identical one would come back from the cache
        retry = messages + [
            {"role": "assistant", "content": first.text},
            {"role": "user", "content": RETRY},
        ]
        calls.append(llm.chat("judge", retry, json_mode=True, trace=trace, max_tokens=1024))
        got = parse_scores(calls[-1].text)
    cost = sum(c.cost_usd for c in calls)  # llm.chat already put each call on the trace ledger
    if isinstance(got, str):
        raise JudgeFailed(f"{got} after one retry: {calls[-1].text[:200]!r}")
    return {**got, "model": calls[-1].model, "cost_usd": cost}
