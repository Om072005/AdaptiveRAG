"""Cost aware model selector: the small model unless the question looks hard."""

from adaptiverag.config import router_cfg
from adaptiverag.types import ModelSize, Retrieved, RouteDecision


def choose_model(
    decision: RouteDecision, retrieved: Retrieved, context_tokens: int
) -> tuple[ModelSize, str]:
    """Small or large model, with the reason string stored on the trace."""
    cfg = router_cfg()["select"]
    if decision.final in cfg["large_if_routes"]:
        return "large", f"large:route {decision.final}"
    label = decision.classification.label if decision.classification else None
    if label in cfg["large_if_labels"]:
        return "large", f"large:label {label}"
    if context_tokens > cfg["large_if_context_tokens"]:
        return "large", f"large:context {context_tokens} tokens > {cfg['large_if_context_tokens']}"
    return (
        "small",
        f"small:route {decision.final}, label {label or 'none'}, {context_tokens} tokens",
    )
