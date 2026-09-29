"""Entity resolution (06_DECISIONS.md D9): normalize names, block, merge, write alias rows."""

import re
from typing import Any

from adaptiverag.ingest.validate import match_form
from adaptiverag.types import Triple

# dropped from the end of a name so "Apple Inc." and "Apple" resolve together; merges still need
# the same entity type, so a person named like a company is never folded into it
ORG_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "ltd",
    "limited",
    "llc",
    "plc",
}
APOSTROPHE = re.compile(r"['’]s\b|['’]")


def join_initials(words: list[str]) -> list[str]:
    """['j', 'r', 'r', 'tolkien'] -> ['jrr', 'tolkien']: a run of single letters is one token."""
    out: list[str] = []
    after_letter = False
    for w in words:
        if len(w) == 1 and after_letter:
            out[-1] += w
        else:
            out.append(w)
        after_letter = len(w) == 1
    return out


def normalize_name(s: str) -> str:
    """'The Apple Computer Co., Inc.' -> 'apple computer'; 'J. R. R. Tolkien' -> 'jrr tolkien'."""
    words = join_initials(match_form(APOSTROPHE.sub("", s.replace("&", " and "))).split())
    while len(words) > 1 and words[-1] in ORG_SUFFIXES:
        words.pop()
    if len(words) > 1 and words[0] == "the":
        words.pop(0)
    return " ".join(words)


def blocking_key(s: str) -> str:
    """Normalized first token. Only names in the same block (and of the same type) are compared."""
    words = normalize_name(s).split()
    return words[0] if words else ""


def trigrams(s: str) -> set[str]:
    """pg_trgm style trigrams: each normalized word padded with two spaces before, one after."""
    grams: set[str] = set()
    for w in normalize_name(s).split():
        padded = f"  {w} "
        grams.update(padded[i : i + 3] for i in range(len(padded) - 2))
    return grams


def trigram_sim(a: str, b: str) -> float:
    """Shared trigrams over all trigrams, the measure pg_trgm's similarity() uses."""
    ta, tb = trigrams(a), trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta or tb else 0.0


def resolve(
    triples: list[Triple],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """(entities, aliases, relations) rows."""
    raise NotImplementedError
