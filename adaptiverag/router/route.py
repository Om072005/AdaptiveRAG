from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Mode, Retrieved, RouteDecision


def route_and_retrieve(question: str, mode: Mode, trace: Trace) -> tuple[RouteDecision, Retrieved]:
    """At most one fallback, always to hybrid."""
    raise NotImplementedError
