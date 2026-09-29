"""The generation prompt: numbered context blocks and the answer format bind_citations parses."""

from adaptiverag.types import Retrieved

NOT_ENOUGH = "not enough context"

SYSTEM = f"""You answer questions using only the numbered context blocks you are given.

Reply in exactly this format:
Answer: <the shortest span that answers the question, or "{NOT_ENOUGH}">
<one or two sentences explaining it; put [n] after every claim, n = the block it is from>

Rules:
- Use only facts in the blocks. If they do not answer it, write "Answer: {NOT_ENOUGH}".
- The answer line is a short span (a name, date, number, yes or no), not a sentence.
- Cite only block numbers that exist. Never cite outside knowledge."""


def context_blocks(retrieved: Retrieved) -> str:
    """Hits as [n] Title / text blocks in rank order, n starting at 1."""
    hits = sorted(retrieved.hits, key=lambda h: h.rank)
    return "\n\n".join(f"[{n}] {h.title}\n{h.text}" for n, h in enumerate(hits, start=1))


def graph_facts(retrieved: Retrieved) -> list[str]:
    """One line per path edge, '(subject) -[predicate]-> (object) [n]', n = its provenance block.

    An edge whose source chunk is not among the blocks is left out: a fact must be citable.
    """
    block = {h.chunk_id: n for n, h in enumerate(sorted(retrieved.hits, key=lambda h: h.rank), 1)}
    lines: list[str] = []
    for path in retrieved.paths:
        for e in path.edges:
            if e.chunk_id not in block:
                continue
            line = f"({e.subject_name}) -[{e.predicate}]-> ({e.object_name}) [{block[e.chunk_id]}]"
            if line not in lines:
                lines.append(line)
    return lines


def build_prompt(question: str, retrieved: Retrieved) -> list[dict[str, str]]:
    """Messages with numbered context blocks [1]..[k] in hit rank order, then graph facts if any."""
    user = f"Context:\n\n{context_blocks(retrieved)}"
    facts = graph_facts(retrieved)
    if facts:
        user += "\n\nGraph facts (each comes from the block in brackets):\n" + "\n".join(facts)
    user += f"\n\nQuestion: {question}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
