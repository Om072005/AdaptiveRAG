import io
from typing import Any

from adaptiverag.demo.show import LivePrinter, describe


def step(name: str, **data: Any) -> dict[str, Any]:
    return {"type": "step", "step": name, "at_ms": 5, **data}


def test_steps_print_numbered_and_the_answer_streams_under_them() -> None:
    out = io.StringIO()
    p = LivePrinter(out)
    p(step("embed", model="nomic-embed-text", dims=768, cached=False, ms=41))
    p({"type": "delta", "kind": "thinking", "text": "Block 1 says\n2000."})
    p({"type": "delta", "kind": "answer", "text": "Answer: "})
    p({"type": "delta", "kind": "answer", "text": "2000"})
    p(step("fallback", why="graph_no_path", to="hybrid"))
    assert out.getvalue().splitlines() == [
        "  1 embed      nomic-embed-text, 768 dims  41 ms",
        "    thinking   Block 1 says",
        "               2000.",
        "    answer     Answer: 2000",
        "  2 fallback   graph_no_path, so hybrid",
    ]


def test_link_shows_five_entities_and_counts_the_rest() -> None:
    seeds = [{"name": f"E{i}", "score": 1.0, "matched": f"E{i}", "type": "ORG"} for i in range(8)]
    (line,) = describe(step("link", seeds=seeds))
    assert line == "E0 1.00, E1 1.00, E2 1.00, E3 1.00, E4 1.00, and 3 more"


def test_a_question_without_context_says_no_model_was_called() -> None:
    assert describe(step("model", size=None, model=None, reason="no_context")) == [
        "no chunks, so no model call: not enough context"
    ]


def test_entities_that_share_a_name_show_once_with_a_count() -> None:
    seeds = [
        {"name": "Bryce Courtenay", "score": 1.0, "matched": "Bryce Courtenay", "type": "PERSON"},
        {"name": "Bryce Courtenay", "score": 1.0, "matched": "Bryce Courtenay", "type": "PERSON"},
        {"name": "Juan Carlos", "score": 0.86, "matched": "Juan Carlos", "type": "PERSON"},
    ]
    assert describe(step("link", seeds=seeds)) == [
        "Bryce Courtenay 1.00 (2 entities), Juan Carlos 0.86"
    ]
