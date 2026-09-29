import re
from pathlib import Path

from adaptiverag.config import ROOT
from adaptiverag.eval import judge
from adaptiverag.types import Answer, Edge, GraphPath, Hit, Retrieved

SNAPSHOT = Path(__file__).parent / "snapshots" / "judge_prompt.txt"


def read(path: Path) -> str:
    # a checkout on Windows may turn line endings into CRLF
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def sample() -> tuple[Answer, Retrieved]:
    hits = [
        Hit("c2", "d2", "Jane Roe", "Jane Roe later worked for Globex.", 0.7, "graph", 2),
        Hit("c1", "d1", "Acme Rockets", "Acme Rockets was founded by Jane Roe.", 0.8, "graph", 1),
    ]
    edges = (
        Edge("r1", "e1", "Acme Rockets", "founded_by", "e2", "Jane Roe", "c1", 0.9),
        Edge("r2", "e2", "Jane Roe", "worked_for", "e3", "Globex", "c2", 0.8),
        Edge("r3", "e3", "Globex", "located_in", "e4", "Ohio", "c9", 0.5),  # chunk not in context
    )
    retrieved = Retrieved(hits, [GraphPath(edges, 0.72, True)], [], 0.72, True, 10)
    text = "Answer: Globex\nJane Roe founded Acme Rockets [1] and later worked for Globex [2]."
    answer = Answer("Globex", text, [], "openai/gpt-oss-120b", "large", "r", 0.9, 1, 1, 0.0, 1)
    return answer, retrieved


def test_judge_prompt_matches_snapshot() -> None:
    answer, retrieved = sample()
    content = judge.build_messages(
        "What company did the founder of Acme Rockets later work for?", answer, retrieved
    )[0]["content"]
    assert content == read(SNAPSHOT)


def test_context_blocks_follow_rank_and_skip_facts_without_a_block() -> None:
    _, retrieved = sample()
    blocks = judge.context_blocks(retrieved)
    assert blocks.startswith("[1] Acme Rockets:")
    assert "(Jane Roe) -[worked_for]-> (Globex) [2]" in blocks
    assert "Ohio" not in blocks
    assert (
        judge.context_blocks(Retrieved([], [], [], 0.0, False, 0)) == "(no context was retrieved)"
    )


def test_rubric_in_docs_matches_the_prompt() -> None:
    doc = read(ROOT / "docs" / "eval-protocol.md")
    block = re.search(r"<!-- rubric:start -->\n```text\n(.*?)\n```\n<!-- rubric:end -->", doc, re.S)
    assert block is not None and block.group(1) == judge.RUBRIC
