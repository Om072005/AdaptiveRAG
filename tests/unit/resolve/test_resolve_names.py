import pytest

from adaptiverag.ingest.resolve import (
    blocking_key,
    join_initials,
    normalize_name,
    trigram_sim,
    trigrams,
)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("Apple Inc.", "apple"),
        ("Apple", "apple"),
        ("The Apple Computer Co., Inc.", "apple computer"),
        ("The Beatles", "beatles"),
        ("The", "the"),
        ("Beyoncé", "beyonce"),
        ("Tim Burton's", "tim burton"),
        ("O’Brien", "obrien"),
        ("Simon & Garfunkel", "simon and garfunkel"),
        ("Company", "company"),
        ("Sammy Davis Jr.", "sammy davis jr"),
        ("", ""),
    ],
)
def test_normalize_name(raw: str, normalized: str) -> None:
    assert normalize_name(raw) == normalized


def test_initials_are_one_token_however_they_are_written() -> None:
    forms = ["J. R. R. Tolkien", "J.R.R. Tolkien", "JRR Tolkien", "j r r tolkien"]
    assert {normalize_name(f) for f in forms} == {"jrr tolkien"}
    assert {blocking_key(f) for f in forms} == {"jrr"}
    assert join_initials(["malcolm", "x"]) == ["malcolm", "x"]
    assert join_initials(["a", "b", "smith", "c"]) == ["ab", "smith", "c"]


def test_company_and_short_name_share_a_block() -> None:
    assert blocking_key("Apple Inc.") == blocking_key("Apple") == "apple"
    assert blocking_key("The Walt Disney Company") == blocking_key("Walt Disney") == "walt"
    assert blocking_key("Tim Burton") != blocking_key("Timothy Burton")
    assert blocking_key("...") == ""


def test_trigrams_follow_pg_trgm_padding() -> None:
    assert trigrams("Cat") == {"  c", " ca", "cat", "at "}
    assert trigrams("Apple Inc.") == trigrams("apple")


def test_trigram_similarity() -> None:
    assert trigram_sim("Apple Inc.", "Apple") == 1.0
    assert trigram_sim("Tim Burton", "tim burton") == 1.0
    sim = trigram_sim("New York", "New York City")
    assert sim == trigram_sim("New York City", "New York")
    assert 0.5 < sim < 0.92
    assert trigram_sim("Tim Burton", "Johnny Depp") == 0.0
    assert trigram_sim("", "") == 0.0
