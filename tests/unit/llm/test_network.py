import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.config import models

pytestmark = pytest.mark.network


@pytest.mark.parametrize("role", ["small", "large", "classify", "extract", "judge"])
def test_one_chat_per_role(role: str) -> None:
    r = llm.chat(
        role, [{"role": "user", "content": "Reply with the single word: ok"}], max_tokens=256
    )  # type: ignore[arg-type]
    assert r.model == models()[role].model  # type: ignore[index]
    assert r.tokens_in > 0 and r.tokens_out > 0 and r.cost_usd > 0


def test_embed_three_texts_unit_norm() -> None:
    vecs = llm.embed(["Paris is the capital of France.", "Ankara", "a third sentence"])
    assert vecs.shape == (3, 768)
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-5)


def test_same_call_twice_is_cached_with_original_tokens_and_latency() -> None:
    msgs = [{"role": "user", "content": "Reply with the single word: cached"}]
    first = llm.chat("small", msgs, max_tokens=256)
    second = llm.chat("small", msgs, max_tokens=256)
    assert second.cached
    assert (second.tokens_in, second.tokens_out, second.latency_ms) == (
        first.tokens_in,
        first.tokens_out,
        first.latency_ms,
    ) or first.cached  # already cached by an earlier run: both come from the same row
