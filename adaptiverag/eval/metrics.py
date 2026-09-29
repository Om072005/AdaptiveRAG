from adaptiverag.types import Hit


def normalize_answer(s: str) -> str:
    """HotpotQA official normalisation."""
    raise NotImplementedError


def em(pred: str, gold: str) -> float:
    raise NotImplementedError


def f1(pred: str, gold: str) -> float:
    raise NotImplementedError


def recall_at_k(hits: list[Hit], supporting_titles: list[str], k: int) -> float:
    raise NotImplementedError


def mrr(hits: list[Hit], supporting_titles: list[str]) -> float:
    raise NotImplementedError


def sp_precision(hits: list[Hit], supporting_spans: list[tuple[str, int, int]]) -> float:
    """Share of retrieved characters inside supporting sentences."""
    raise NotImplementedError
