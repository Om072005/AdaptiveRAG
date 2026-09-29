import hashlib
import re
import unicodedata

WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Unicode NFC and collapsed whitespace."""
    return WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def doc_id(source: str, title: str) -> str:
    """First 16 hex of sha1(source + '|' + title)."""
    return hashlib.sha1(f"{source}|{title}".encode()).hexdigest()[:16]


def join_sentences(sentences: list[str]) -> tuple[str, tuple[tuple[int, int], ...]]:
    """Normalize each sentence and join with one space; returns the text and a span per sentence."""
    text = ""
    spans: list[tuple[int, int]] = []
    for raw in sentences:
        sentence = normalize(raw)
        if sentence:
            text += " " if text else ""
            spans.append((len(text), len(text) + len(sentence)))
            text += sentence
        else:
            # keep a zero length span so a sentence index from the dataset still lines up
            spans.append((len(text), len(text)))
    return text, tuple(spans)
