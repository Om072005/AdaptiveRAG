from typing import Any

import pytest

from adaptiverag.eval import judge
from adaptiverag.types import LLMResult
from tests.unit.eval.test_judge_prompt import sample

GOOD = '{"faithfulness": 5, "relevance": 3, "completeness": 1, "rationale": "ok"}'


class FakeTrace:
    def __init__(self) -> None:
        self.fields: dict[str, Any] = {}

    def set(self, **fields: Any) -> None:
        self.fields.update(fields)


def fake_chat(replies: list[str], calls: list[list[dict[str, str]]]) -> Any:
    def chat(role: str, messages: list[dict[str, str]], **kw: Any) -> LLMResult:
        assert role == "judge" and kw["json_mode"]
        calls.append(messages)
        text = replies[len(calls) - 1]
        return LLMResult(text, "judge", "gemini-x", 100, 20, 0.001, 30, False, False, 0, 0)

    return chat


def test_parse_scores_maps_1_to_5_onto_0_to_1() -> None:
    assert judge.parse_scores(GOOD) == {
        "faithfulness": 1.0,
        "relevance": 0.5,
        "completeness": 0.0,
        "rationale": "ok",
    }


@pytest.mark.parametrize(
    ("raw", "why"),
    [
        ("nope", "not json"),
        ("[1, 2]", "not a json object"),
        ('{"faithfulness": 6, "relevance": 3, "completeness": 3}', "faithfulness is not"),
        ('{"faithfulness": 4, "relevance": 3.5, "completeness": 3}', "relevance is not"),
        ('{"faithfulness": 4, "relevance": "3", "completeness": 3}', "relevance is not"),
        ('{"faithfulness": 4, "relevance": 3, "completeness": true}', "completeness is not"),
        ('{"faithfulness": 4, "relevance": 3}', "completeness is not"),
    ],
)
def test_parse_scores_rejects_invalid_replies(raw: str, why: str) -> None:
    got = judge.parse_scores(raw)
    assert isinstance(got, str) and got.startswith(why)


def test_judge_scores_and_puts_cost_on_the_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[dict[str, str]]] = []
    monkeypatch.setattr(judge.llm, "chat", fake_chat([GOOD], calls))
    trace = FakeTrace()
    answer, retrieved = sample()
    got = judge.judge("q?", answer, retrieved, trace)  # type: ignore[arg-type]
    assert len(calls) == 1 and got["faithfulness"] == 1.0 and got["model"] == "gemini-x"
    assert trace.fields == {"eval_cost_usd": 0.001} and got["cost_usd"] == 0.001


def test_bad_json_is_retried_once_with_a_different_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[dict[str, str]]] = []
    monkeypatch.setattr(judge.llm, "chat", fake_chat(["oops", GOOD], calls))
    trace = FakeTrace()
    answer, retrieved = sample()
    got = judge.judge("q?", answer, retrieved, trace)  # type: ignore[arg-type]
    assert len(calls) == 2 and calls[1][:1] == calls[0]
    assert calls[1][-1]["content"] == judge.RETRY
    assert got["relevance"] == 0.5 and trace.fields["eval_cost_usd"] == pytest.approx(0.002)


def test_second_bad_reply_is_a_failure_not_a_score(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[dict[str, str]]] = []
    monkeypatch.setattr(judge.llm, "chat", fake_chat(["oops", '{"faithfulness": 9}'], calls))
    trace = FakeTrace()
    answer, retrieved = sample()
    with pytest.raises(judge.JudgeFailed, match="faithfulness is not an integer"):
        judge.judge("q?", answer, retrieved, trace)  # type: ignore[arg-type]
    assert len(calls) == 2 and trace.fields["eval_cost_usd"] == pytest.approx(0.002)
