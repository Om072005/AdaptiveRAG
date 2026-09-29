import re
import string
from collections import Counter

from adaptiverag.types import Hit

# The official script scores a yes/no answer 0 unless both sides match exactly
YES_NO = {"yes", "no", "noanswer"}


def normalize_answer(s: str) -> str:
    """HotpotQA official normalisation: lower case, no punctuation, no articles, single spaces."""
    s = "".join(ch for ch in s.lower() if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def em(pred: str, gold: str) -> float:
    """1.0 when the normalized answers are equal, else 0.0."""
    return float(normalize_answer(pred) == normalize_answer(gold))


def f1(pred: str, gold: str) -> float:
    """Token F1 between the normalized answers, as in the HotpotQA script."""
    p, g = normalize_answer(pred), normalize_answer(gold)
    if (p in YES_NO or g in YES_NO) and p != g:
        return 0.0
    p_tokens, g_tokens = p.split(), g.split()
    same = sum((Counter(p_tokens) & Counter(g_tokens)).values())
    if same == 0:
        return 0.0
    precision, recall = same / len(p_tokens), same / len(g_tokens)
    return 2 * precision * recall / (precision + recall)


def recall_at_k(hits: list[Hit], supporting_titles: list[str], k: int) -> float:
    """Share of distinct supporting titles that appear among the top k hits by rank."""
    gold = set(supporting_titles)
    if not gold:
        return 0.0
    found = {h.title for h in sorted(hits, key=lambda h: h.rank)[:k]}
    return len(gold & found) / len(gold)


def mrr(hits: list[Hit], supporting_titles: list[str]) -> float:
    """1 / position of the first hit from a supporting title, 0.0 if none is retrieved."""
    gold = set(supporting_titles)
    for position, h in enumerate(sorted(hits, key=lambda h: h.rank), start=1):
        if h.title in gold:
            return 1.0 / position
    return 0.0


def sp_precision(hits: list[Hit], supporting_spans: list[tuple[str, int, int]]) -> float:
    """Share of retrieved characters inside supporting sentences."""
    raise NotImplementedError
