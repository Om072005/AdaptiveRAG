import re
from dataclasses import replace
from pathlib import Path

import pytest

from adaptiverag.config import ingest_cfg
from adaptiverag.ingest.validate import match_form, occurs, validate
from adaptiverag.types import Triple

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    "Ed Wood is a 1994 American biographical period comedy-drama film directed and produced "
    "by Tim Burton, and starring Johnny Depp as cult filmmaker Ed Wood. "
    "Beyoncé sang at its Los Angeles premiere."
)
GOOD = Triple("Tim Burton", "PERSON", "directed", "Ed Wood", "WORK", "d1:sentence:0", 65, 100, 0.9)


def test_match_form_drops_case_accents_and_punctuation() -> None:
    assert match_form("Beyoncé, Inc.") == "beyonce inc"
    assert match_form("  J.R.R.  Tolkien ") == "j r r tolkien"
    assert match_form("snake_case") == "snake case"
    assert match_form("?!") == ""


@pytest.mark.parametrize(
    "triple",
    [
        GOOD,
        replace(GOOD, subject="TIM BURTON"),
        replace(GOOD, subject="Johnny Depp", predicate="starred_in"),
        replace(GOOD, subject="Beyonce", object="Los Angeles", predicate="performed_in"),
        replace(GOOD, subject="Johny Depp"),  # fuzzy, ratio 0.95
        replace(GOOD, subject="Tim Burtin"),  # fuzzy, ratio exactly 0.9: the bar is inclusive
    ],
)
def test_good_triples_pass(triple: Triple) -> None:
    assert validate(triple, SOURCE) is None


@pytest.mark.parametrize(
    ("triple", "reason"),
    [
        (replace(GOOD, subject="Christopher Nolan"), "subject_not_in_source"),
        (replace(GOOD, subject="Tim Bortin"), "subject_not_in_source"),  # ratio 0.8
        (replace(GOOD, object="Batman Returns"), "object_not_in_source"),
        (replace(GOOD, object="rect"), "object_not_in_source"),  # inside 'directed' only
        (replace(GOOD, subject="  "), "empty"),
        (replace(GOOD, object="..."), "empty"),
        (replace(GOOD, predicate=""), "empty"),
        (replace(GOOD, object="tim burton."), "self_loop"),
    ],
)
def test_bad_triples_get_their_reason(triple: Triple, reason: str) -> None:
    assert validate(triple, SOURCE) == reason


def test_every_reason_is_allowed_by_the_database() -> None:
    sql = (ROOT / "db" / "migrations" / "0001_init.sql").read_text(encoding="utf-8")
    found = re.search(r"reason in \(([^)]*)\)", sql)
    assert found is not None
    allowed = {r.strip(" '") for r in found.group(1).split(",")}
    returned = {"subject_not_in_source", "object_not_in_source", "empty", "self_loop"}
    assert returned <= allowed


def test_occurs_needs_whole_words() -> None:
    assert occurs("Ed Wood", SOURCE, 0.9)
    assert not occurs("Wood is a 1995", SOURCE, 1.0)
    assert not occurs("Ted", "directed by", 0.9)
    assert not occurs("", SOURCE, 0.9)


def test_the_bar_comes_from_config() -> None:
    assert ingest_cfg()["extract"]["fuzzy_ratio"] == 0.9
