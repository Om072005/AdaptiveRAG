import pytest

from adaptiverag.router.classify import FEATURES, classify, classify_rules, features
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
    assert c.confidence == max(c.probs.values())
    assert sum(c.probs.values()) == pytest.approx(1.0)


def test_a_question_without_cues_is_not_confident() -> None:
    c = classify_rules("Tim Burton films released after the long strike ended in Burbank")
    assert c.confidence == pytest.approx(1 / 3)


def test_classify_dispatches_on_method() -> None:
    trace = Trace("q", "auto", "cli")
    assert classify("When was Zach Woods born?", None, trace, method="rules").method == "rules"  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        classify("When was Zach Woods born?", None, trace, method="llm")  # type: ignore[arg-type]
