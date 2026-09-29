import json
from pathlib import Path

import pytest

from adaptiverag.ingest.chunking import split_sentences
from adaptiverag.ingest.loader import from_records

FIXTURE = Path(__file__).parent / "fixtures" / "hotpot_3q.json"


def sentences(text: str) -> list[str]:
    return [text[s:e] for s, e in split_sentences(text)]


def test_plain_sentences() -> None:
    assert sentences("Paris is big. Lyon is smaller! Is Nice small? Yes.") == [
        "Paris is big.",
        "Lyon is smaller!",
        "Is Nice small?",
        "Yes.",
    ]


def test_titles_do_not_end_a_sentence() -> None:
    text = "Mr. Smith met Dr. Jones in St. Louis. They talked."
    assert sentences(text) == ["Mr. Smith met Dr. Jones in St. Louis.", "They talked."]


def test_dotted_acronyms_and_initials() -> None:
    text = "The U.S. Army hired J. K. Rowling, e.g. as a writer. She left."
    assert sentences(text) == ["The U.S. Army hired J. K. Rowling, e.g. as a writer.", "She left."]


def test_decimals_are_not_boundaries() -> None:
    text = "The film earned $3.5 million in 1994. It won 2.5 awards."
    assert sentences(text) == ["The film earned $3.5 million in 1994.", "It won 2.5 awards."]


def test_closing_quotes_stay_with_their_sentence() -> None:
    text = 'He said "Go home." Then he left. “Why?” she asked.'
    assert sentences(text) == ['He said "Go home."', "Then he left.", "“Why?” she asked."]


def test_quoted_exclamation_mid_sentence_does_not_split() -> None:
    assert sentences('"Help!" was a hit single. It sold well.') == [
        '"Help!" was a hit single.',
        "It sold well.",
    ]


def test_parentheses() -> None:
    text = "Ed Wood Jr. (born 1924) was a director. He won (in 1990). (He lost later.) The end."
    assert sentences(text) == [
        "Ed Wood Jr. (born 1924) was a director.",
        "He won (in 1990).",
        "(He lost later.)",
        "The end.",
    ]


def test_lowercase_next_word_continues_the_sentence() -> None:
    assert sentences("He sold apples, pears etc. and plums. Done.") == [
        "He sold apples, pears etc. and plums.",
        "Done.",
    ]


def test_months_and_numbers() -> None:
    text = "It opened on Jan. 5, 1990 as No. 1 in the chart. It closed."
    assert sentences(text) == ["It opened on Jan. 5, 1990 as No. 1 in the chart.", "It closed."]


def test_last_sentence_without_punctuation() -> None:
    assert sentences("One. Two without a stop") == ["One.", "Two without a stop"]


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_text(text: str) -> None:
    assert split_sentences(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "  Leading space.  Two  spaces between.\nNew line!  ",
        "Mr. A. B. Smith (b. 1950) lived in the U.S. He left. “Ok.”",
        "no punctuation at all",
    ],
)
def test_every_non_space_character_is_covered_once(text: str) -> None:
    spans = split_sentences(text)
    covered = [i for s, e in spans for i in range(s, e)]
    assert covered == sorted(set(covered))
    assert {i for i, ch in enumerate(text) if not ch.isspace()} <= set(covered)
    for s, e in spans:
        assert not text[s].isspace() and not text[e - 1].isspace()


def test_recovers_the_dataset_sentences_on_the_fixture() -> None:
    docs, _ = from_records(json.loads(FIXTURE.read_text(encoding="utf-8")), 3)
    for d in docs:
        assert split_sentences(d.text) == [(s, e) for s, e in d.sentences if e > s]
