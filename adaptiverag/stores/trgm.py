"""pg_trgm's word_similarity() in Python, for databases without the extension (the embedded demo
database). A port of calc_word_similarity and iterate_word_similarity in contrib/pg_trgm/trgm_op.c,
plain (not strict) mode: same trigrams, same extent search, same float4 rounding, so an alias the
SQL path keeps is kept here too. tests/unit/test_trgm.py pins it against values from pg_trgm."""

import unicodedata

import numpy as np


def trigrams(text: str) -> list[str]:
    """Trigrams in text order, repeats kept: every run of letters and digits lowercased, two
    spaces before and one after, then each window of three characters. A word character is what
    Postgres counts: letters, decimal digits and letter numerals ('Ⅻ'), but not '²' or '½'."""
    out: list[str] = []
    word: list[str] = []
    for ch in text.lower() + " ":
        if ch.isalpha() or ch.isdecimal() or unicodedata.category(ch) == "Nl":
            word.append(ch)
        elif word:
            padded = "  " + "".join(word) + " "
            out.extend(padded[i : i + 3] for i in range(len(padded) - 2))
            word = []
    return out


def _sml(count: int, len1: int, len2: int) -> np.float32:
    # CALCSML in float4, so ties and the >= threshold land where Postgres puts them
    return np.float32(count) / np.float32(len1 + len2 - count)


def word_similarity(needle: str, haystack: str) -> float:
    """Greatest similarity between the trigrams of needle and any continuous extent of the ordered
    trigrams of haystack: word_similarity(needle, haystack) in SQL."""
    t1 = set(trigrams(needle))
    t2 = trigrams(haystack)
    ids: dict[str, int] = {}
    index = [ids.setdefault(t, len(ids)) for t in t2]  # trg2indexes: one id per distinct trigram
    found = [t in t1 for t in ids]
    ulen1 = len(t1)

    lastpos = [-1] * len(ids)
    ulen2 = count = 0
    lower, upper = -1, -1
    best = np.float32(0.0)
    for i, tid in enumerate(index):
        if lower >= 0 or found[tid]:
            if lastpos[tid] < 0:
                ulen2 += 1
                if found[tid]:
                    count += 1
            lastpos[tid] = i
        if not found[tid]:
            continue
        upper = i
        if lower == -1:
            lower, ulen2 = i, 1
        cur = _sml(count, ulen1, ulen2)
        # also try every later lower bound, keeping the one that scores best
        tmp_count, tmp_ulen2, prev_lower = count, ulen2, lower
        for tmp_lower in range(lower, upper + 1):
            tmp = _sml(tmp_count, ulen1, tmp_ulen2)
            if tmp > cur:
                cur, ulen2, lower, count = tmp, tmp_ulen2, tmp_lower, tmp_count
            t = index[tmp_lower]
            if lastpos[t] == tmp_lower:
                tmp_ulen2 -= 1
                if found[t]:
                    tmp_count -= 1
        best = max(best, cur)
        for tmp_lower in range(prev_lower, lower):
            t = index[tmp_lower]
            if lastpos[t] == tmp_lower:
                lastpos[t] = -1
    return float(best)
