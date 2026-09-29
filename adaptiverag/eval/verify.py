"""Hand verification of gold items: a reviewer walks a numbered range, accepting or flagging."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from adaptiverag.eval.gold import GoldItem, problems, read_jsonl, write_jsonl

Sentences = dict[tuple[str, int], str]
HELP = "y = correct as is, n = wrong (you type what is wrong), s = skip, q = save and quit"


def numbered(gold_dir: Path) -> list[tuple[int, GoldItem]]:
    """Items 1..150: dev file order, then test file order."""
    # verification reads test.jsonl directly: checking a question is not running the test split
    items = read_jsonl(gold_dir / "dev.jsonl") + read_jsonl(gold_dir / "test.jsonl")
    return list(enumerate(items, start=1))


def render(n: int, item: GoldItem, sentences: Sentences) -> str:
    lines = [
        f"#{n} {item.id} [{item.type}, {item.split}]",
        f"  Q: {item.question}",
        f"  A: {item.answer}",
    ]
    for title, i in item.supporting_sentences:
        text = sentences.get((title, i), "(sentence not found in the corpus)")
        lines.append(f"  {title} #{i}: {text}")
    if item.notes:
        lines.append(f"  notes: {item.notes}")
    if item.verified_by:
        lines.append(f"  already verified by {item.verified_by}")
    return "\n".join(lines)


def apply(item: GoldItem, choice: str, reviewer: str, note: str = "") -> None:
    """y marks the item verified by the reviewer; n clears it and records what is wrong."""
    if choice == "y":
        item.verified_by = reviewer
    elif choice == "n":
        item.verified_by = ""
        item.notes = f"{item.notes}; {reviewer}: {note}" if item.notes else f"{reviewer}: {note}"


def load_sentences(items: list[GoldItem]) -> Sentences:
    """Supporting sentence text from the local HotpotQA file, so no ingested corpus is needed."""
    from adaptiverag.eval.gold import FULL_QUESTIONS
    from adaptiverag.ingest.loader import load_hotpot

    titles = {t for i in items for t in i.supporting_titles}
    docs = [d for d in load_hotpot(FULL_QUESTIONS)[0] if d.title in titles]
    return {(d.title, i): d.text[s:e] for d in docs for i, (s, e) in enumerate(d.sentences)}


def run(
    gold_dir: Path,
    first: int,
    last: int,
    reviewer: str,
    ask: Callable[[str], str] = input,
    sentences: Callable[[list[GoldItem]], Sentences] = load_sentences,
) -> dict[str, int]:
    """Walk items first..last, saving both files after every answer. Returns the counts."""
    all_items = numbered(gold_dir)
    todo = [(n, i) for n, i in all_items if first <= n <= last]
    texts = sentences([i for _, i in todo])
    counts = {"y": 0, "n": 0, "s": 0}
    print(HELP)
    for n, item in todo:
        print(render(n, item, texts))
        for p in problems(item):
            print(f"  check: {p}")
        choice = ""
        while choice not in ("y", "n", "s", "q"):
            choice = ask("  [y/n/s/q] ").strip().lower()
        if choice == "q":
            break
        apply(item, choice, reviewer, ask("  what is wrong: ") if choice == "n" else "")
        counts[choice] += 1
        save(gold_dir, [i for _, i in all_items])
    return counts


def save(gold_dir: Path, items: list[GoldItem]) -> None:
    write_jsonl(gold_dir / "dev.jsonl", [i for i in items if i.split == "dev"])
    write_jsonl(gold_dir / "test.jsonl", [i for i in items if i.split == "test"])


def status(gold_dir: Path) -> dict[str, Any]:
    """Unverified item numbers and problems that block G0."""
    items = numbered(gold_dir)
    return {
        "total": len(items),
        "unverified": [n for n, i in items if not i.verified_by.strip()],
        "problems": {n: p for n, i in items if (p := problems(i, final=True))},
    }
