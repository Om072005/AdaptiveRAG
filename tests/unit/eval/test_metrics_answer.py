import re
import string
from collections import Counter

import pytest

from adaptiverag.eval.metrics import em, f1, normalize_answer


# Reference: normalize_answer, f1_score and exact_match_score from the official
# hotpot_evaluate_v1.py, copied as is so our versions are checked against it.
def ref_normalize_answer(s):
    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def ref_f1_score(prediction, ground_truth):
    normalized_prediction = ref_normalize_answer(prediction)
    normalized_ground_truth = ref_normalize_answer(ground_truth)
    ZERO_METRIC = (0, 0, 0)
    if (
        normalized_prediction in ["yes", "no", "noanswer"]
        and normalized_prediction != normalized_ground_truth
    ):
        return ZERO_METRIC
    if (
        normalized_ground_truth in ["yes", "no", "noanswer"]
        and normalized_prediction != normalized_ground_truth
    ):
        return ZERO_METRIC
    prediction_tokens = normalized_prediction.split()
    ground_truth_tokens = normalized_ground_truth.split()
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return ZERO_METRIC
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1, precision, recall


def ref_exact_match_score(prediction, ground_truth):
    return ref_normalize_answer(prediction) == ref_normalize_answer(ground_truth)


# (prediction, gold, expected em, expected f1)
CASES = [
    ("Globex", "Globex", 1.0, 1.0),
    ("the Globex Corporation.", "Globex Corporation", 1.0, 1.0),
    ("Globex Inc", "Globex Corporation", 0.0, 0.5),
    ("yes", "no", 0.0, 0.0),
    ("Yes.", "yes", 1.0, 1.0),
    ("no, it was not", "no", 0.0, 0.0),
    ("Alpha Town", "Alpha Town, Ohio", 0.0, 0.8),
    ("", "Delta", 0.0, 0.0),
    ("New York New York", "New York", 0.0, 2 / 3),
    ("An American rock band", "American", 0.0, 0.5),
]


@pytest.mark.parametrize(("pred", "gold", "want_em", "want_f1"), CASES)
def test_em_and_f1_match_official_script(
    pred: str, gold: str, want_em: float, want_f1: float
) -> None:
    assert normalize_answer(pred) == ref_normalize_answer(pred)
    assert em(pred, gold) == float(ref_exact_match_score(pred, gold)) == want_em
    assert f1(pred, gold) == pytest.approx(ref_f1_score(pred, gold)[0])
    assert f1(pred, gold) == pytest.approx(want_f1)


def test_normalize_answer_strips_articles_punctuation_and_spaces() -> None:
    assert normalize_answer("  The  Beatles, an English band! ") == "beatles english band"
