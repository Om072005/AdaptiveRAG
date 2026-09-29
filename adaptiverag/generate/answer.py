from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Answer, ModelSize, Retrieved, RouteDecision


def synthesize(
    question: str,
    decision: RouteDecision,
    retrieved: Retrieved,
    trace: Trace,
    force_size: ModelSize | None = None,
) -> Answer:
    """Pick the model, generate, bind citations and score answer confidence."""
    raise NotImplementedError
