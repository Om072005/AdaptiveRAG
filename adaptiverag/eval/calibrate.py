"""python -m adaptiverag.eval.calibrate <judged dev run_id>

How well answer confidence predicts judge faithfulness (the README's open question about the two
confidences), and the [answer] weights and threshold that would predict it best. Prints a
suggestion only; M1 applies it to config/router.toml.
"""

import argparse
from typing import Any

import numpy as np

from adaptiverag.config import router_cfg
from adaptiverag.generate.confidence import citation_coverage, retrieval_strength
from adaptiverag.types import Citation, Hit, Retrieved

WEIGHT_GRID = [round(0.05 * i, 2) for i in range(21)]  # w_citation 0.00 .. 1.00
THRESHOLD_GRID = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation, None when either side is constant or there are fewer than 3 points."""
    if len(xs) < 3 or np.std(xs) == 0 or np.std(ys) == 0:
        return None
    return float(np.corrcoef(xs, ys)[0, 1])


def components(
    detail: dict[str, Any], route: str, top_score: float, path_found: bool
) -> tuple[float, float] | None:
    """(citation coverage, retrieval strength) recomputed from a stored QueryResponse, or None if
    the trace predates the serializer and has no citations stored."""
    answer = detail.get("answer")
    if not isinstance(answer, dict) or "citations" not in answer:
        return None
    citations = [
        Citation(c["n"], c["chunk_id"], "", c.get("title", ""), "") for c in answer["citations"]
    ]
    # retrieval_strength only reads hit sources, top_score and path_found
    hit = Hit("", "", "", "", 0.0, route, 1)  # type: ignore[arg-type]
    retrieved = Retrieved([hit], [], [], top_score, path_found, 0)
    strength = retrieval_strength(retrieved, float(router_cfg()["vector"]["min_top_score"]))
    return citation_coverage(answer["text"], citations), strength


def best_weight(parts: list[tuple[float, float]], faith: list[float]) -> tuple[float, float | None]:
    """The w_citation (w_retrieval = 1 - w) whose confidence correlates best with faithfulness."""
    scored = []
    for w in WEIGHT_GRID:
        conf = [w * cov + (1 - w) * strength for cov, strength in parts]
        scored.append((w, pearson(conf, faith)))
    valid = [s for s in scored if s[1] is not None]
    return max(valid, key=lambda s: s[1] or 0) if valid else (WEIGHT_GRID[0], None)


def best_threshold(conf: list[float], faith: list[float], flag_below: float) -> tuple[float, float]:
    """The answer.min_confidence that most often flags exactly the answers the judge would flag."""

    def accuracy(t: float) -> float:
        return float(
            np.mean([(c < t) == (f < flag_below) for c, f in zip(conf, faith, strict=True)])
        )

    return max(((t, accuracy(t)) for t in THRESHOLD_GRID), key=lambda s: s[1])


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.calibrate")
    p.add_argument("run_id")
    args = p.parse_args(argv)
    from adaptiverag.stores import db

    cfg = router_cfg()
    with db.conn() as c:
        rows = c.execute(
            "select r.faithfulness, t.answer_confidence, t.detail, r.route_taken, t.top_score,"
            " t.path_found from eval_results r join traces t on t.trace_id = r.trace_id"
            " where r.run_id = %s and r.faithfulness is not null"
            " and t.answer_confidence is not null",
            (args.run_id,),
        ).fetchall()
    faith = [float(r[0]) for r in rows]
    stored = [float(r[1]) for r in rows]
    print(f"{len(rows)} judged answers with answer confidence in {args.run_id}")
    print(f"correlation of stored answer confidence with faithfulness: {pearson(stored, faith)}")
    w = cfg["answer"]
    print(f"current: w_citation {w['w_citation']}, w_retrieval {w['w_retrieval']},", end=" ")
    print(f"min_confidence {w['min_confidence']}")
    found = [
        (components(r[2], r[3], float(r[4] or 0), bool(r[5])), f)
        for r, f in zip(rows, faith, strict=True)
    ]
    usable = [(parts, f) for parts, f in found if parts is not None]
    if len(usable) < len(rows):
        missing = len(rows) - len(usable)
        print(f"{missing} traces have no stored citations and are left out of the weight search")
    if not usable:
        return
    weight, corr = best_weight([u[0] for u in usable], [u[1] for u in usable])
    reweighted = [weight * cov + (1 - weight) * strength for (cov, strength), _ in usable]
    t, acc = best_threshold(reweighted, [u[1] for u in usable], cfg["judge"]["flag_below"])
    print(f"best w_citation {weight} (w_retrieval {round(1 - weight, 2)}), correlation {corr}")
    print(f"best min_confidence {t}: agrees with the judge's flag on {acc:.3f} of answers")
    print("\nsuggested config/router.toml change (not applied):")
    print(f"[answer] w_citation = {w['w_citation']} -> {weight}")
    print(f"[answer] w_retrieval = {w['w_retrieval']} -> {round(1 - weight, 2)}")
    print(f"[answer] min_confidence = {w['min_confidence']} -> {t}")


if __name__ == "__main__":
    main()
