from collections.abc import Callable

import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.router import hybrid
from adaptiverag.stores import vector
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit, LLMResult


def hit(chunk_id: str, rank: int) -> Hit:
    return Hit(chunk_id, "d", f"Title {chunk_id}", f"text {chunk_id}", 0.5, "vector", rank)


HITS = [hit("a", 1), hit("b", 2), hit("c", 3)]


def fake_chat(reply: str, prompts: list[str]) -> Callable[..., LLMResult]:
    def chat(
        role: str,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        trace: Trace | None = None,
        **kw: object,
    ) -> LLMResult:
        prompts.append(messages[0]["content"])
        r = LLMResult(reply, "small", "m", 100, 10, 0.00001, 5, False, False, 0, 0)
        if trace is not None:
            trace.add_llm(r)
        return r

    return chat


def test_the_model_order_is_applied_and_priced_on_the_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(llm, "chat", fake_chat('{"order": [3, 1, 2]}', prompts))
    trace = Trace("which one?", "hybrid", "cli")
    ranked = hybrid.llm_rerank("which one?", HITS, trace)
    assert [(h.chunk_id, h.rank) for h in ranked] == [("c", 1), ("a", 2), ("b", 3)]
    assert len(trace.calls) == 1 and trace.calls[0].cost_usd > 0
    assert "Question: which one?" in prompts[0] and "[3] Title c: text c" in prompts[0]


def test_left_out_and_bad_numbers_never_drop_a_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm, "chat", fake_chat('{"order": [2, 2, 9, "x", true]}', []))
    ranked = hybrid.llm_rerank("q", HITS, Trace("q", "hybrid", "cli"))
    assert [h.chunk_id for h in ranked] == ["b", "a", "c"]


@pytest.mark.parametrize(
    "reply", ["not json", '{"rank": [1]}', '{"order": "3,1"}', '{"order": [0, 7]}']
)
def test_unusable_reply_keeps_the_order_and_is_noted(
    monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    monkeypatch.setattr(llm, "chat", fake_chat(reply, []))
    trace = Trace("q", "hybrid", "cli")
    assert hybrid.llm_rerank("q", HITS, trace) == HITS
    assert "rerank_error" in trace.fields["detail"]


def test_off_by_default_in_merge_rerank(monkeypatch: pytest.MonkeyPatch) -> None:
    assert router_cfg()["hybrid"]["llm_rerank"] is False
    monkeypatch.setattr(vector, "chunk_vectors", lambda ids: {})

    def no_chat(*args: object, **kw: object) -> LLMResult:
        raise AssertionError("rerank is off")

    monkeypatch.setattr(llm, "chat", no_chat)
    trace = Trace("q", "hybrid", "cli")
    assert len(hybrid.merge_rerank(HITS, [], np.ones(3), 8, trace)) == 3
    assert trace.calls == []


def test_one_hit_needs_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm, "chat", fake_chat("{}", []))
    trace = Trace("q", "hybrid", "cli")
    assert hybrid.llm_rerank("q", HITS[:1], trace) == HITS[:1] and trace.calls == []
