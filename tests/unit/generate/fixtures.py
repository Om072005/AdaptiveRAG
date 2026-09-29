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


def two_hop() -> Retrieved:
    """A 2 hop path: who founded X, then where that person worked. Edges cite blocks 1 and 2."""
    from adaptiverag.types import Edge, GraphPath, Seed

    hits = [
        hit(1, "Acme Robotics", "Acme Robotics was founded by Jane Doe in 1999.", 0.9, "graph"),
        hit(2, "Jane Doe", "Jane Doe later joined Globex as chief engineer.", 0.8, "graph"),
    ]
    e1 = Edge(
        "r1", "e_acme", "Acme Robotics", "founded_by", "e_jane", "Jane Doe", "d1:sentence:0", 0.9
    )
    e2 = Edge("r2", "e_jane", "Jane Doe", "worked_for", "e_globex", "Globex", "d2:sentence:0", 0.8)
    stray = Edge("r3", "e_jane", "Jane Doe", "born_in", "e_x", "Nowhere", "d9:sentence:0", 0.5)
    paths = [GraphPath((e1, e2), 0.72, True), GraphPath((e1, stray), 0.1, False)]
    seeds = [Seed("e_acme", "Acme Robotics", "ORG", 0.95, "Acme Robotics")]
    return Retrieved(
        hits=hits, paths=paths, seeds=seeds, top_score=0.72, path_found=True, latency_ms=9
    )
