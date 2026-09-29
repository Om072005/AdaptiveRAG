"""The only module that talks to model providers: chat and embeddings, cached, priced, capped."""

from typing import TYPE_CHECKING

import numpy as np

from adaptiverag.types import LLMResult, Role

if TYPE_CHECKING:
    from adaptiverag.telemetry.trace import Trace


class BudgetExceeded(Exception):
    """Raised on the 5th LLM call inside one trace (the cost spiral guard)."""


class RateLimited(Exception):
    """Raised after 5 failed attempts on 429 or 5xx; eval runs save progress and resume later."""


def chat(
    role: Role,
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    trace: "Trace | None" = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> LLMResult:
    """One chat completion for a role from config/models.toml."""
    raise NotImplementedError


def embed(texts: list[str], *, trace: "Trace | None" = None) -> np.ndarray:
    """(n, 768) float32, L2 normalized, sent in batches of 100."""
    raise NotImplementedError
