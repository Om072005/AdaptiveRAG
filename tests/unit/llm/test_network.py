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
