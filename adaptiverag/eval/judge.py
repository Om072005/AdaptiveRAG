from typing import Any

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Answer, Retrieved

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


def judge(question: str, answer: Answer, retrieved: Retrieved, trace: Trace) -> dict[str, Any]:
    """{faithfulness, relevance, completeness in 0..1, rationale}."""
    raise NotImplementedError
