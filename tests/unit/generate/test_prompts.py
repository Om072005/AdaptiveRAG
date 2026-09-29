from pathlib import Path

from adaptiverag.generate.prompts import build_prompt

from .fixtures import retrieved

SNAPSHOT = Path(__file__).parent / "snapshots" / "prompt.txt"


def render(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"### {m['role']}\n{m['content']}" for m in messages) + "\n"


def test_prompt_matches_snapshot() -> None:
    text = render(
        build_prompt(
            "What is the capital of the country whose largest city is Istanbul?", retrieved()
        )
    )
    if not SNAPSHOT.exists():  # first run writes it; review the file before committing
        SNAPSHOT.write_text(text, encoding="utf-8", newline="\n")
    assert text == SNAPSHOT.read_text(encoding="utf-8")


def test_blocks_follow_hit_rank_not_list_order() -> None:
    user = build_prompt("q", retrieved())[1]["content"]
    assert user.index("[1] Istanbul") < user.index("[2] Ankara")


GRAPH_SNAPSHOT = Path(__file__).parent / "snapshots" / "prompt_graph.txt"


def test_graph_prompt_matches_snapshot() -> None:
    from .fixtures import two_hop

    text = render(
        build_prompt(
            "What company did the person who founded Acme Robotics later work for?", two_hop()
        )
    )
    if not GRAPH_SNAPSHOT.exists():
        GRAPH_SNAPSHOT.write_text(text, encoding="utf-8", newline="\n")
    assert text == GRAPH_SNAPSHOT.read_text(encoding="utf-8")


def test_every_fact_line_ends_with_a_valid_block_and_stray_edges_are_dropped() -> None:
    import re

    from adaptiverag.generate.prompts import graph_facts

    from .fixtures import two_hop

    facts = graph_facts(two_hop())
    assert facts == [
        "(Acme Robotics) -[founded_by]-> (Jane Doe) [1]",
        "(Jane Doe) -[worked_for]-> (Globex) [2]",
    ]
    assert all(1 <= int(re.search(r"\[(\d+)\]$", f).group(1)) <= 2 for f in facts)  # type: ignore[union-attr]


def test_vector_prompt_has_no_graph_section() -> None:
    assert "Graph facts" not in build_prompt("q", retrieved())[1]["content"]
