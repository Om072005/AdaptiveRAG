import hashlib
import unicodedata

from adaptiverag.ingest.normalize import doc_id, join_sentences, normalize


def test_normalize_collapses_whitespace_and_strips() -> None:
    assert normalize("  Paris\tis \n the capital.  ") == "Paris is the capital."


def test_normalize_composes_unicode() -> None:
    decomposed = "Beyoncé"
    assert normalize(decomposed) == "Beyoncé"
    assert unicodedata.is_normalized("NFC", normalize(decomposed))


def test_normalize_is_idempotent() -> None:
    for text in ["", "  a  b ", "Café au lait", "line\r\nbreak\tand  tabs"]:
        once = normalize(text)
        assert normalize(once) == once


def test_doc_id_is_stable_and_16_hex() -> None:
    first = doc_id("hotpotqa-dev", "Ed Wood")
    assert first == doc_id("hotpotqa-dev", "Ed Wood")
    assert len(first) == 16 and int(first, 16) >= 0
    assert first != doc_id("hotpotqa-dev", "Ed Wood (film)")
    assert first != doc_id("other", "Ed Wood")


def test_doc_id_matches_the_contract_formula() -> None:
    assert (
        doc_id("hotpotqa-dev", "Ed Wood") == hashlib.sha1(b"hotpotqa-dev|Ed Wood").hexdigest()[:16]
    )


def test_sentence_offsets_map_back_to_the_text() -> None:
    raw = ["Ed Wood is a 1994 film.", " It was directed by  Tim Burton.", " It stars Johnny Depp."]
    text, spans = join_sentences(raw)
    assert text == "Ed Wood is a 1994 film. It was directed by Tim Burton. It stars Johnny Depp."
    assert [text[s:e] for s, e in spans] == [normalize(r) for r in raw]


def test_empty_sentence_keeps_its_index() -> None:
    text, spans = join_sentences(["First one.", "   ", "Third one."])
    assert len(spans) == 3
    assert spans[1][0] == spans[1][1]
    assert text[spans[2][0] : spans[2][1]] == "Third one."
    assert text == "First one. Third one."


def test_joined_text_is_already_normalized() -> None:
    text, _ = join_sentences([" á ", "b  c", "", " d"])
    assert normalize(text) == text
