from adaptiverag.types import ModelSize, Retrieved, RouteDecision


def choose_model(
    decision: RouteDecision, retrieved: Retrieved, context_tokens: int
) -> tuple[ModelSize, str]:
    """Small or large model, with the reason string stored on the trace."""
    raise NotImplementedError
