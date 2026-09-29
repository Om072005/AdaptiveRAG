from typing import Any

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Answer, Retrieved


def judge(question: str, answer: Answer, retrieved: Retrieved, trace: Trace) -> dict[str, Any]:
    """{faithfulness, relevance, completeness in 0..1, rationale}."""
    raise NotImplementedError
