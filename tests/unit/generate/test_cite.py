from adaptiverag.generate.cite import bind_citations, invalid_markers

from .fixtures import retrieved


def test_valid_markers_become_citations_in_order() -> None:
    raw = "Answer: Ankara\nIstanbul is the largest city in Turkey [1], whose capital is Ankara [2]."
    short, text, cites = bind_citations(raw, retrieved())
    assert short == "Ankara"
    assert text.startswith("Ankara. Istanbul is") and "[1]" in text and "[2]" in text
    assert [(c.n, c.title) for c in cites] == [(1, "Istanbul"), (2, "Ankara")]
    assert cites[0].chunk_id == "d1:sentence:0" and cites[0].snippet.startswith("Istanbul")


def test_out_of_range_markers_are_dropped_and_counted() -> None:
    raw = "Answer: Ankara\nThe capital is Ankara [2][7], see also [1, 9]."
    short, text, cites = bind_citations(raw, retrieved())
    assert "[7]" not in text and "[1]" in text and "9" not in text
    assert [c.n for c in cites] == [2, 1]
    assert invalid_markers(raw, 2) == 2


def test_no_markers_gives_no_citations() -> None:
    short, text, cites = bind_citations("Answer: Ankara\nIt is the capital.", retrieved())
    assert (short, cites) == ("Ankara", [])


def test_not_enough_context_is_kept_as_the_answer() -> None:
    short, text, cites = bind_citations(
        "Answer: Not enough context.\nThe blocks do not say [1].", retrieved()
    )
    assert (short, text, cites) == ("not enough context", "not enough context", [])


def test_markdown_answer_line_and_trailing_period() -> None:
    short, _, _ = bind_citations("**Answer:** Ankara.\nBecause [2].", retrieved())
    assert short == "Ankara"


def test_missing_answer_line_uses_first_line() -> None:
    short, _, cites = bind_citations("Ankara\nIt is the capital [2].", retrieved())
    assert short == "Ankara" and [c.n for c in cites] == [2]
