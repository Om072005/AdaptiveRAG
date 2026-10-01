import pytest

from adaptiverag.stores.trgm import trigrams, word_similarity

# word_similarity(lower(a), lower(q)) as pg_trgm 1.6 on Neon returned it (float4, read as float8).
# The port was also compared on 1.5 million alias x question pairs of the corpus: no difference.
PG_TRGM = [
    ("word", "two words", 0.800000011920929),
    ("ab", "b a b a", 0.3333333432674408),
    ("Ⅻ", "Ⅻ x", 1.0),
    ("48.48 km²", "48.48 km² area", 1.0),
    ("48.48 km²", "Richford is a town in Franklin County Vermont", 0.0),
    ("½ mile", "½ mile", 1.0),
    ("São Paulo", "Was São Paulo founded?", 1.0),
    ("Tim Burton", "Who directed Ed Wood, Tim Burton or Tim Allen?", 1.0),
    ("", "", 0.0),
    ("x", "", 0.0),
]


@pytest.mark.parametrize(("needle", "haystack", "expected"), PG_TRGM)
def test_matches_pg_trgm(needle: str, haystack: str, expected: float) -> None:
    assert word_similarity(needle.lower(), haystack.lower()) == expected


def test_trigrams_pad_each_word_and_drop_punctuation() -> None:
    assert trigrams("Ab, c!") == ["  a", " ab", "ab ", "  c", " c "]


def test_superscript_two_ends_a_word() -> None:
    assert trigrams("km²") == ["  k", " km", "km "]
