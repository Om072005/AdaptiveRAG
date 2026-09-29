import pytest

from adaptiverag.config import router_cfg
from adaptiverag.generate.cite import bind_citations
from adaptiverag.generate.confidence import answer_confidence, citation_coverage, retrieval_strength

from .fixtures import retrieved


def weights() -> tuple[float, float, float]:
    cfg = router_cfg()
    return cfg["answer"]["w_citation"], cfg["answer"]["w_retrieval"], cfg["vector"]["min_top_score"]


def test_full_coverage_and_strong_retrieval() -> None:
    r = retrieved(top_score=0.9)
    _, text, cites = bind_citations(
        "Answer: Ankara\nIstanbul is largest [1]. Ankara is capital [2].", r
    )
    wc, wr, _ = weights()
    assert citation_coverage(text, cites) == 1.0
    assert answer_confidence(text, cites, r) == pytest.approx(wc + wr)


def test_partial_coverage() -> None:
    r = retrieved(top_score=0.9)
    _, text, cites = bind_citations(
        "Answer: Ankara\nIstanbul is largest [1]. Ankara is capital.", r
    )
    assert citation_coverage(text, cites) == 0.5


def test_zero_coverage_weak_retrieval() -> None:
    wc, wr, min_top = weights()
    r = retrieved(top_score=min_top / 2)
    _, text, cites = bind_citations("Answer: Ankara\nIt is the capital.", r)
    assert answer_confidence(text, cites, r) == pytest.approx(wr * 0.5)


def test_not_enough_context_scores_zero() -> None:
    r = retrieved()
    _, text, cites = bind_citations("Answer: not enough context", r)
    assert answer_confidence(text, cites, r) == 0.0


def test_graph_and_hybrid_strength() -> None:
    _, _, min_top = weights()
    assert retrieval_strength(retrieved(path_found=True, source="graph"), min_top) == 1.0
    assert retrieval_strength(retrieved(path_found=False, source="graph"), min_top) == 0.3
    hybrid = retrieved(top_score=min_top, path_found=False, source="hybrid")
    assert retrieval_strength(hybrid, min_top) == pytest.approx((1.0 + 0.3) / 2)
