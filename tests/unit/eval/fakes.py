"""A fake QueryResult for eval tests, until the real pipeline lands."""

from adaptiverag.types import Answer, Classification, Hit, QueryResult, Retrieved, RouteDecision

TRACE_ID = "00000000-0000-4000-8000-000000000001"


def fake_result(short: str, titles: list[str], trace_id: str = TRACE_ID) -> QueryResult:
    hits = [
        Hit(f"{t}:sentence:0", f"doc_{t}", t, "x" * 20, 0.8, "vector", n)
        for n, t in enumerate(titles, start=1)
    ]
    c = Classification("multi_hop", 0.9, {"multi_hop": 0.9}, "logreg", 0.0, 1)
    decision = RouteDecision("auto", c, "graph", "hybrid", ["graph_no_path->hybrid"])
    answer = Answer(short, short, [], "m", "large", "r", 0.7, 100, 10, 0.001, 50)
    return QueryResult(
        trace_id, decision, Retrieved(hits, [], [], 0.8, False, 5), answer, 0.002, 120, False
    )
