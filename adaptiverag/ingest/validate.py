"""Source validation: keep a triple only if both entity names occur in the chunk it came from."""

import re
import unicodedata
from difflib import SequenceMatcher

from adaptiverag.config import ingest_cfg
from adaptiverag.types import Triple

NOT_WORD = re.compile(r"[\W_]+")


def match_form(s: str) -> str:
    """Case folded, accents and punctuation dropped: 'Beyoncé, Inc.' -> 'beyonce inc'."""
    decomposed = unicodedata.normalize("NFKD", s.casefold())
    bare = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return NOT_WORD.sub(" ", bare).strip()


def occurs(name: str, text: str, min_ratio: float) -> bool:
    """True if name matches a run of whole words in text, exactly or at ratio >= min_ratio."""
    target, words = match_form(name), match_form(text).split()
    if not target:
        return False
    if f" {target} " in f" {' '.join(words)} ":
        return True
    # one word more or fewer, so a split or joined word still lines up
    n = len(target.split())
    for size in sorted({max(1, n - 1), n, n + 1}):
        for i in range(len(words) - size + 1):
            m = SequenceMatcher(None, " ".join(words[i : i + size]), target)
            if m.quick_ratio() >= min_ratio and m.ratio() >= min_ratio:
                return True
    return False


def validate(t: Triple, source_text: str) -> str | None:
    """None = ok, else a reject reason from the extraction_rejects schema.

    'empty' means a blank subject, predicate or object; source_text is the chunk text.
    """
    min_ratio = float(ingest_cfg()["extract"]["fuzzy_ratio"])
    subject, obj = match_form(t.subject), match_form(t.object)
    if not subject or not obj or not t.predicate.strip():
        return "empty"
    if subject == obj:
        return "self_loop"
    if not occurs(t.subject, source_text, min_ratio):
        return "subject_not_in_source"
    if not occurs(t.object, source_text, min_ratio):
        return "object_not_in_source"
    return None
