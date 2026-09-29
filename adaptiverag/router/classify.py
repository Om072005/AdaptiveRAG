"""Query classifiers: rules on cue features (this file), logistic regression and few shot LLM."""

import re
import time

import numpy as np

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


def classify_rules(question: str) -> Classification:
    """Label with the most votes; probabilities are the vote shares with one added per label,
    so a question with no clear cue gets a low confidence instead of a confident guess."""
    started = time.perf_counter()
    votes = rule_votes(features(question))
    total = sum(votes.values()) + len(LABELS)
    probs: dict[str, float] = {label: (votes[label] + 1) / total for label in LABELS}
    # ties go to the order of LABELS, cheapest route first
    label = max(LABELS, key=lambda lb: probs[lb])
    ms = int((time.perf_counter() - started) * 1000)
    return Classification(label, probs[label], probs, "rules", 0.0, ms)


def classify(
    question: str, qvec: np.ndarray, trace: Trace, method: str | None = None
) -> Classification:
    """method: 'rules' | 'logreg' | 'llm'; default from router.toml."""
    method = method or router_cfg()["classifier"]["method"]
    if method == "rules":
        return classify_rules(question)
    raise NotImplementedError(f"classifier method {method!r} is not built yet")
