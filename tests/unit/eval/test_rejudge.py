from types import SimpleNamespace
from typing import Any

from adaptiverag.eval import judge, rejudge
from adaptiverag.telemetry.trace import Trace

VERDICT = {"faithfulness": 1.0, "relevance": 0.75, "completeness": 0.5, "rationale": "ok"}


def fake_answer(calls: list[tuple[Any, ...]]) -> Any:
    def answer(question: str, mode: str, source: str, force_size: str | None) -> Any:
        calls.append((question, mode, source, force_size))
        return SimpleNamespace(answer=f"answer to {question}", retrieved=f"hits for {question}")

    return answer


def test_only_missing_questions_are_judged_and_stored_on_the_run_trace() -> None:
    answered: list[tuple[Any, ...]] = []
    stored: list[tuple[str, str, dict[str, Any]]] = []
    seen: list[tuple[str, Any, Any]] = []

    def judge_one(q: str, a: Any, r: Any, t: Trace) -> dict[str, Any]:
        seen.append((q, a, r))
        return VERDICT

    judged, failed = rejudge.rejudge(
        [("q1", "trace-1"), ("q3", "trace-3")],
        {"q1": "Who?", "q2": "When?", "q3": "Where?"},
        "auto",
        "large",
        fake_answer(answered),
        judge_one,
        lambda qid, tid, v, jt: stored.append((qid, tid, v)),
    )
    assert (judged, failed) == (2, [])
    # rebuilt through the pipeline with the run's mode and size, never counted as an eval trace
    assert answered == [
        ("Who?", "auto", "cli", "large"),
        ("Where?", "auto", "cli", "large"),
    ]
    assert seen[0] == ("Who?", "answer to Who?", "hits for Who?")
    assert stored == [("q1", "trace-1", VERDICT), ("q3", "trace-3", VERDICT)]


def test_a_second_failure_is_reported_not_stored() -> None:
    stored: list[Any] = []

    def judge_one(q: str, a: Any, r: Any, t: Trace) -> dict[str, Any]:
        raise judge.JudgeFailed("not json after one retry")

    judged, failed = rejudge.rejudge(
        [("q1", "trace-1")],
        {"q1": "Who?"},
        "vector",
        None,
        fake_answer([]),
        judge_one,
        lambda *a: stored.append(a),
    )
    assert (judged, failed, stored) == (0, ["q1"], [])
