"""Query classifiers: rules on cue features, logistic regression and a few shot model."""

import json
import re
import time
from functools import cache
from pathlib import Path
from typing import cast

import numpy as np

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Classification, QType

LABELS: tuple[QType, ...] = ("single_hop", "multi_hop", "comparison")

# one line per cue feature, in the order features() returns them
FEATURES = (
    ("or_choice", "two options joined by 'or', as in 'X or Y?'"),
    ("both_either", "'both', 'either' or 'neither'"),
    ("shared", "'same', 'in common', 'share', 'different' or 'similar'"),
    (
        "comparative",
        "an ordering word: older, younger, first, last, earlier, later, more, fewer...",
    ),
    ("yes_no", "starts with an auxiliary verb: are, is, was, were, do, does, did, has, have, can"),
    ("and_names", "two capitalized names joined by 'and'"),
    (
        "relative_clause",
        "who, whom, whose, which, that or where after the opening, not after a preposition",
    ),
    ("possessive", "a possessive 's"),
    ("of_chain", "'of the' or 'of a' phrases, capped at 3, divided by 3"),
    ("names", "capitalized words after the first word, capped at 5, divided by 5"),
    ("length", "words, capped at 40, divided by 40"),
    ("wh_start", "starts with a wh-word, or a preposition then which or what ('In which year')"),
)

WORD = re.compile(r"[\w'’-]+")
COMPARATIVE = {
    "older", "younger", "oldest", "youngest", "first", "last", "earlier", "later", "earliest",
    "latest", "more", "most", "fewer", "less", "larger", "smaller", "bigger", "higher", "lower",
    "longer", "shorter", "taller", "closer", "further", "farther",
}  # fmt: skip
AUXILIARY = {"are", "is", "was", "were", "do", "does", "did", "has", "have", "had", "can"}
WH = {"what", "who", "whom", "when", "where", "which", "why", "how", "whose"}
RELATIVE = {"who", "whom", "whose", "which", "that", "where"}
PREPOSITIONS = {
    "in",
    "of",
    "on",
    "at",
    "by",
    "for",
    "from",
    "to",
    "with",
    "about",
    "during",
    "among",
}
AND_NAMES = re.compile(r"\b[A-Z][\w'’.-]*(?: [A-Z][\w'’.-]*)* and [A-Z]")
OF_CHAIN = re.compile(r"\bof (?:the|a|an)\b", re.IGNORECASE)
POSSESSIVE = re.compile(r"\w['’]s\b")


def features(question: str) -> np.ndarray:
    """Hand written cue features, documented one per line in FEATURES."""
    words = WORD.findall(question)
    lower = [w.lower() for w in words]
    first = lower[0] if lower else ""
    text = " ".join(lower)
    rest = set(lower[1:])
    # "in which year" opens a question; "the film which was remade" nests one
    relative = any(
        w in RELATIVE and lower[i - 1] not in PREPOSITIONS for i, w in enumerate(lower) if i >= 2
    )
    opening = first in WH or (first in PREPOSITIONS and lower[1:2] in (["which"], ["what"]))
    values = [
        " or " in f" {text} ",
        bool(rest & {"both", "either", "neither"}) or first in {"both", "either", "neither"},
        bool(re.search(r"\b(same|in common|share[ds]?|different|similar)\b", text)),
        bool(set(lower) & COMPARATIVE),
        first in AUXILIARY,
        bool(AND_NAMES.search(question)),
        relative,
        bool(POSSESSIVE.search(question)),
        min(len(OF_CHAIN.findall(question)), 3) / 3,
        min(sum(w[:1].isupper() for w in words[1:]), 5) / 5,
        min(len(words), 40) / 40,
        opening,
    ]
    return np.array(values, dtype=np.float32)


def rule_votes(f: np.ndarray) -> dict[QType, float]:
    """Each cue votes for the label it points at; a short plain wh-question votes single hop."""
    cue = dict(zip((name for name, _ in FEATURES), f.tolist(), strict=True))
    comparison = (
        cue["or_choice"]
        + cue["both_either"]
        + cue["shared"]
        + cue["and_names"]
        + cue["comparative"] * max(cue["or_choice"], cue["and_names"])
        + cue["yes_no"] * cue["and_names"]
    )
    multi_hop = (
        cue["relative_clause"]
        + cue["possessive"]
        + (cue["of_chain"] > 0)
        + (cue["length"] * 40 >= 15)
    )
    # single hop is what is left: a short question that opens with a wh-word and has no cue above
    plain = comparison == 0 and multi_hop == 0 and cue["length"] * 40 < 12
    single_hop = cue["wh_start"] * plain
    return {"single_hop": single_hop, "multi_hop": multi_hop, "comparison": comparison}


RULES_CALIBRATION = Path(__file__).parent / "weights" / "rules.json"
MAX_MARGIN = 3  # leads of three votes or more share one bucket


def rule_bucket(votes: dict[QType, float]) -> tuple[QType, int]:
    """The label with the most votes and its lead over the runner up, capped at MAX_MARGIN.
    Ties go to the order of LABELS, cheapest route first."""
    ranked = sorted(LABELS, key=lambda lb: -votes[lb])
    return ranked[0], min(round(votes[ranked[0]] - votes[ranked[1]]), MAX_MARGIN)


@cache
def load_rules_calibration(path: Path = RULES_CALIBRATION) -> dict[str, dict[str, int]]:
    """True label counts per bucket, written by python -m adaptiverag.router.train rules."""
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run python -m adaptiverag.router.train rules")
    return dict(json.loads(path.read_text(encoding="utf-8"))["buckets"])


def classify_rules(question: str, path: Path = RULES_CALIBRATION) -> Classification:
    """Label with the most votes. The probabilities are the shares of each true label among the
    training questions in the same bucket (winning label, lead in votes), with one added per
    label, so a bucket the training set never filled stays at a third each."""
    started = time.perf_counter()
    label, margin = rule_bucket(rule_votes(features(question)))
    counts = load_rules_calibration(path).get(f"{label} {margin}", {})
    total = sum(counts.values()) + len(LABELS)
    probs: dict[str, float] = {lb: (counts.get(lb, 0) + 1) / total for lb in LABELS}
    ms = int((time.perf_counter() - started) * 1000)
    return Classification(label, probs[label], probs, "rules", 0.0, ms)


WEIGHTS = Path(__file__).parent / "weights" / "logreg.npz"


def logreg_inputs(question: str, qvec: np.ndarray) -> np.ndarray:
    """One input row of the logistic regression: [query embedding, cue features]."""
    return np.concatenate([np.asarray(qvec, dtype=np.float32), features(question)])


def softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(axis=-1, keepdims=True))
    return np.asarray(e / e.sum(axis=-1, keepdims=True))


@cache
def load_logreg(path: Path = WEIGHTS) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    """Weights, bias and label order written by python -m adaptiverag.router.train."""
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run python -m adaptiverag.router.train")
    data = np.load(path)
    return data["W"], data["b"], tuple(str(x) for x in data["labels"])


def classify_logreg(question: str, qvec: np.ndarray, path: Path = WEIGHTS) -> Classification:
    """Softmax over the trained weights; its top probability is the classifier confidence. The
    query embedding is reused from retrieval, so the call costs nothing."""
    started = time.perf_counter()
    w, b, labels = load_logreg(path)
    p = softmax(logreg_inputs(question, qvec) @ w + b)
    probs = {label: float(p[i]) for i, label in enumerate(labels)}
    label = labels[int(np.argmax(p))]
    ms = int((time.perf_counter() - started) * 1000)
    return Classification(cast(QType, label), probs[label], probs, "logreg", 0.0, ms)


# hand written examples, none taken from the dev or test questions
FEW_SHOT = """Label the question by what answering it takes, as JSON probabilities for three labels:
single_hop: one fact about one thing.
multi_hop: a chain, where one fact names the thing a second fact is about.
comparison: two named things compared, or checked for something in common.

Question: When was the Eiffel Tower completed?
{"single_hop": 0.95, "multi_hop": 0.04, "comparison": 0.01}
Question: What instrument does the singer of the band that recorded Wonderwall play?
{"single_hop": 0.05, "multi_hop": 0.92, "comparison": 0.03}
Question: Which river is longer, the Danube or the Rhine?
{"single_hop": 0.03, "multi_hop": 0.02, "comparison": 0.95}
Question: In which city is the university that Marie Curie's husband attended?
{"single_hop": 0.06, "multi_hop": 0.9, "comparison": 0.04}
Question: Were Mozart and Haydn both born in Austria?
{"single_hop": 0.04, "multi_hop": 0.06, "comparison": 0.9}
Question: How many moons does Mars have?
{"single_hop": 0.96, "multi_hop": 0.03, "comparison": 0.01}

Reply with the JSON object only."""


def llm_probs(text: str) -> dict[str, float]:
    """The model's probabilities, normalized; missing or broken output counts as no opinion."""
    try:
        raw = json.loads(text)
        values = {label: max(float(raw.get(label, 0.0)), 0.0) for label in LABELS}
    except (ValueError, TypeError, AttributeError):
        values = {label: 0.0 for label in LABELS}
    total = sum(values.values())
    return {k: v / total for k, v in values.items()} if total else {k: 1 / 3 for k in LABELS}


def classify_llm(question: str, trace: Trace) -> Classification:
    """Few shot classification by the 'classify' role, cached, its cost and latency on the trace."""
    messages = [
        {"role": "system", "content": FEW_SHOT},
        {"role": "user", "content": f"Question: {question}"},
    ]
    # gpt-oss reasons before it answers; 512 and 1024 tokens ran out on some dev questions
    max_tokens = int(router_cfg()["classifier"]["llm_max_tokens"])
    r = llm.chat("classify", messages, json_mode=True, trace=trace, max_tokens=max_tokens)
    probs = llm_probs(r.text)
    label = max(LABELS, key=lambda lb: probs[lb])
    return Classification(label, probs[label], probs, "llm", r.cost_usd, r.latency_ms)


def classify(
    question: str, qvec: np.ndarray, trace: Trace, method: str | None = None
) -> Classification:
    """method: 'rules' | 'logreg' | 'llm'; default from router.toml."""
    method = method or router_cfg()["classifier"]["method"]
    if method == "rules":
        return classify_rules(question)
    if method == "logreg":
        return classify_logreg(question, qvec)
    if method == "llm":
        return classify_llm(question, trace)
    raise NotImplementedError(f"classifier method {method!r} is not built yet")
