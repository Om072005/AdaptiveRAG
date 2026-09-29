import json
from pathlib import Path

import pytest

from adaptiverag.config import router_cfg
from adaptiverag.router.classify import (
    FEATURES,
    classify,
    classify_rules,
    features,
    rule_bucket,
)
from adaptiverag.router.train import calibrate_rules
from adaptiverag.telemetry.trace import Trace

NAMES = [name for name, _ in FEATURES]

# one question per cue that should fire it
FIRES = {
    "or_choice": "Who was born first, Tim Burton or Johnny Depp?",
    "both_either": "Are Tim Burton and Johnny Depp both directors?",
    "shared": "What occupation did Tim Burton and Johnny Depp share?",
    "comparative": "Which film is older, Ed Wood or Batman?",
    "yes_no": "Were Tim Burton and Johnny Depp born in the same year?",
    "and_names": "Tim Burton and Johnny Depp worked on which film?",
    "relative_clause": "What company did the person who founded Apple later work for?",
    "possessive": "Who produced Tim Burton's first film?",
    "wh_start": "In which year was Ed Wood released?",
}
PLAIN = "when was ed wood released"


def cue(question: str, name: str) -> float:
    return float(features(question)[NAMES.index(name)])


def test_every_feature_is_documented_in_one_line() -> None:
    assert len(features(PLAIN)) == len(FEATURES)
    assert len(set(NAMES)) == len(NAMES)
    assert all(desc and "\n" not in desc for _, desc in FEATURES)


@pytest.mark.parametrize("name", sorted(FIRES))
def test_each_cue_fires_on_its_example(name: str) -> None:
    assert cue(FIRES[name], name) == 1.0
    if name != "wh_start":
        assert cue(PLAIN, name) == 0.0


def test_which_after_a_preposition_opens_a_question_rather_than_nesting_one() -> None:
    assert cue("In which century was Dundas Castle built?", "relative_clause") == 0.0
    assert (
        cue("Rimo I and Passu Sar are both part of which mountain range?", "relative_clause") == 0.0
    )
    assert cue("Who directed the film which was remade in 2001?", "relative_clause") == 1.0


def test_scaled_counts_stay_in_zero_to_one() -> None:
    long = "What is the name of the son of the brother of the wife of " + "Very " * 60 + "Long?"
    f = features(long)
    assert f.min() >= 0.0 and f.max() <= 1.0
    assert cue(long, "of_chain") == 1.0 and cue(long, "length") == 1.0


@pytest.mark.parametrize(
    ("question", "label"),
    [
        ("Who was born first, Yanka Dyagileva or Alexander Bashlachev?", "comparison"),
        ("Are Stan Lee and Mark Helprin both comic book writers?", "comparison"),
        ("What company did the person who founded X later work for?", "multi_hop"),
        ("When was Zach Woods born?", "single_hop"),
    ],
)
def test_rules_label_clear_questions(question: str, label: str) -> None:
    c = classify_rules(question)
    assert c.label == label and c.method == "rules" and c.cost_usd == 0.0
    assert c.confidence == c.probs[label]
    assert sum(c.probs.values()) == pytest.approx(1.0)


def test_a_question_without_cues_is_not_confident() -> None:
    # the committed calibration: questions with no cue were mostly not single hop in training
    c = classify_rules("Tim Burton films released after the long strike ended in Burbank")
    assert c.confidence < router_cfg()["classifier"]["min_confidence"]


def test_the_bucket_is_the_winner_and_its_capped_lead() -> None:
    assert rule_bucket({"single_hop": 0, "multi_hop": 0, "comparison": 0}) == ("single_hop", 0)
    assert rule_bucket({"single_hop": 0, "multi_hop": 1, "comparison": 1}) == ("multi_hop", 0)
    assert rule_bucket({"single_hop": 0, "multi_hop": 1, "comparison": 5}) == ("comparison", 3)


def test_confidence_is_the_share_of_right_answers_in_the_bucket(tmp_path: Path) -> None:
    one_cue = "Who produced Tim Burton's first film?"
    three_cues = "Who was born first, Tim Burton or Johnny Depp, and did both share a studio?"
    items = [
        {"question": one_cue, "label": "multi_hop"},
        {"question": one_cue, "label": "single_hop"},
        {"question": three_cues, "label": "comparison"},
        {"question": three_cues, "label": "comparison"},
    ]
    buckets = calibrate_rules(items)
    assert buckets == {
        "comparison 3": {"single_hop": 0, "multi_hop": 0, "comparison": 2},
        "multi_hop 1": {"single_hop": 1, "multi_hop": 1, "comparison": 0},
    }
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"buckets": buckets}), encoding="utf-8")
    assert classify_rules(one_cue, path).confidence == pytest.approx(2 / 5)
    assert classify_rules(three_cues, path).confidence == pytest.approx(3 / 5)
    # a bucket the training set never filled
    assert classify_rules("When was Zach Woods born?", path).confidence == pytest.approx(1 / 3)


def test_classify_dispatches_on_method() -> None:
    trace = Trace("q", "auto", "cli")
    assert classify("When was Zach Woods born?", None, trace, method="rules").method == "rules"  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        classify("When was Zach Woods born?", None, trace, method="svm")  # type: ignore[arg-type]
