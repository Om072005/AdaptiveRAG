from adaptiverag.types import Hit, Retrieved


def hit(n: int, title: str, text: str, score: float = 0.8, source: str = "vector") -> Hit:
    return Hit(f"d{n}:sentence:0", f"d{n}", title, text, score, source, n)  # type: ignore[arg-type]


def retrieved(
    top_score: float = 0.8, path_found: bool = False, source: str = "vector"
) -> Retrieved:
    hits = [
        hit(2, "Ankara", "Ankara is the capital of Turkey.", 0.7, source),
        hit(1, "Istanbul", "Istanbul is the largest city in Turkey.", 0.8, source),
    ]
    return Retrieved(
        hits=hits, paths=[], seeds=[], top_score=top_score, path_found=path_found, latency_ms=5
    )
