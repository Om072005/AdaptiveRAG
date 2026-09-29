from typing import Any

import pytest

from adaptiverag.router import classify as classify_mod
from adaptiverag.router.classify import LABELS, classify, llm_probs
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import LLMResult


def test_probabilities_are_normalized_and_broken_output_is_no_opinion() -> None:
    assert llm_probs('{"single_hop": 2, "multi_hop": 1, "comparison": 1}') == {
        "single_hop": 0.5,
        "multi_hop": 0.25,
        "comparison": 0.25,
    }
    for broken in ["not json", "[]", '{"single_hop": -1}', "{}"]:
        assert llm_probs(broken) == {label: pytest.approx(1 / 3) for label in LABELS}


def test_the_model_classifier_records_its_call(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []

    def fake_chat(role: str, messages: list[dict[str, str]], **kw: Any) -> LLMResult:
        seen.append(
            {
                "role": role,
                "json": kw["json_mode"],
                "trace": kw["trace"],
                "user": messages[-1]["content"],
            }
        )
        text = '{"single_hop": 0.1, "multi_hop": 0.2, "comparison": 0.7}'
        return LLMResult(text, "classify", "m", 300, 20, 0.00003, 150, False, False, 0, 0)

    monkeypatch.setattr(classify_mod.llm, "chat", fake_chat)
    trace = Trace("q", "auto", "cli")
    c = classify("Which is older, A or B?", None, trace, method="llm")  # type: ignore[arg-type]
    assert (c.label, c.method, c.cost_usd, c.latency_ms) == ("comparison", "llm", 0.00003, 150)
    assert c.confidence == pytest.approx(0.7)
    assert seen == [
        {
            "role": "classify",
            "json": True,
            "trace": trace,
            "user": "Question: Which is older, A or B?",
        }
    ]
