"""python -m adaptiverag.eval.gold build|split|verify --from N --to M --reviewer <name>"""

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from adaptiverag.config import ROOT, settings

GOLD_DIR = ROOT / "data" / "gold"
RAW_HOTPOT = ROOT / "data" / "raw" / "hotpot_dev_distractor_v1.json"
FULL_MANIFEST = ROOT / "data" / "corpus" / "full.json"

HOTPOT_TYPES = {"bridge": "multi_hop", "comparison": "comparison"}
QTYPES = {"single_hop", "multi_hop", "comparison"}
SPLITS = {"dev", "test"}
# Contract section 4: 40% multi hop, 27% comparison, 33% single hop. 50 * 27% is not whole,
# so test takes 13 comparison and 17 single hop, keeping all 150 at 60 / 40 / 50.
SPLIT_MIX = {
    "dev": {"multi_hop": 40, "comparison": 27, "single_hop": 33},
    "test": {"multi_hop": 20, "comparison": 13, "single_hop": 17},
}


class TestSplitLocked(Exception):
    """Raised when the test split is read without ALLOW_TEST=1."""


@dataclass
class GoldItem:
    """One gold question, the record of contract section 4."""

    id: str
    question: str
    answer: str
    type: str
    split: str  # '' until `split` assigns dev or test
    supporting_titles: list[str]
    supporting_sentences: list[tuple[str, int]]
    source: str
    verified_by: str = ""
    notes: str = ""


def from_hotpot(row: dict[str, Any]) -> GoldItem:
    """Candidate gold item from one HotpotQA dev distractor row (bridge or comparison)."""
    sentences = [(str(t), int(i)) for t, i in row["supporting_facts"]]
    context = {title: sents for title, sents in row["context"]}
    out_of_range = [f"{t}#{i}" for t, i in sentences if i >= len(context.get(t, []))]
    return GoldItem(
        id=f"hp_{row['_id']}",
        question=row["question"],
        answer=row["answer"],
        type=HOTPOT_TYPES[row["type"]],
        split="",
        supporting_titles=list(dict.fromkeys(t for t, _ in sentences)),
        supporting_sentences=sentences,
        source="hotpotqa",
        # HotpotQA has a few supporting facts past the paragraph end; keep them visible for review
        notes=f"supporting sentence out of range: {', '.join(out_of_range)}"
        if out_of_range
        else "",
    )


def build_candidates(rows: list[dict[str, Any]], question_ids: list[str]) -> list[GoldItem]:
    """Multi hop and comparison candidates for corpus questions, in manifest order."""
    by_id = {r["_id"]: r for r in rows}
    return [from_hotpot(by_id[q]) for q in question_ids if q in by_id]


def problems(item: GoldItem, *, final: bool = False) -> list[str]:
    """What is wrong with an item; final=True also requires a split and a named verifier."""
    found = []
    if item.type not in QTYPES:
        found.append(f"type {item.type!r}")
    if not item.question.strip() or not item.answer.strip():
        found.append("empty question or answer")
    if not item.supporting_titles:
        found.append("no supporting titles")
    if {t for t, _ in item.supporting_sentences} - set(item.supporting_titles):
        found.append("supporting sentence outside supporting titles")
    if final and item.split not in SPLITS:
        found.append(f"split {item.split!r}")
    if final and not item.verified_by.strip():
        found.append("not verified")
    return found


def to_json(item: GoldItem) -> str:
    d = asdict(item)
    d["supporting_sentences"] = [list(s) for s in item.supporting_sentences]
    return json.dumps(d, ensure_ascii=False)


def from_json(line: str) -> GoldItem:
    d = json.loads(line)
    d["supporting_sentences"] = [(t, i) for t, i in d["supporting_sentences"]]
    return GoldItem(**d)


def read_jsonl(path: Path) -> list[GoldItem]:
    return [from_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, items: list[GoldItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(to_json(i) + "\n" for i in items), encoding="utf-8")


def split_items(candidates: list[GoldItem], seed: int = 7) -> list[GoldItem]:
    """Draw dev then test per type with a fixed seed; items not drawn are left out."""
    out = []
    for qtype in sorted(QTYPES):
        pool = sorted((c for c in candidates if c.type == qtype), key=lambda c: c.id)
        random.Random(f"{seed}:{qtype}").shuffle(pool)
        need = SPLIT_MIX["dev"][qtype] + SPLIT_MIX["test"][qtype]
        if len(pool) < need:
            raise ValueError(f"{qtype}: {len(pool)} candidates, need {need}")
        n_dev = SPLIT_MIX["dev"][qtype]
        for i, item in enumerate(pool[:need]):
            item.split = "dev" if i < n_dev else "test"
            out.append(item)
    return sorted(out, key=lambda i: (i.split, i.id))


def load_split(
    split: str, gold_dir: Path = GOLD_DIR, allow_test: bool | None = None
) -> list[GoldItem]:
    """Gold items of one split; the test split needs ALLOW_TEST=1."""
    if split == "test" and not (settings().allow_test if allow_test is None else allow_test):
        raise TestSplitLocked("the test split is locked, set ALLOW_TEST=1 (D13 pinned runs only)")
    return read_jsonl(gold_dir / f"{split}.jsonl")


def cmd_build(raw: Path, manifest: Path, out: Path) -> None:
    rows = json.loads(raw.read_text(encoding="utf-8"))
    question_ids = json.loads(manifest.read_text(encoding="utf-8"))["question_ids"]
    items = build_candidates(rows, question_ids)
    write_jsonl(out, items)
    counts = {t: sum(i.type == t for i in items) for t in sorted(QTYPES)}
    print(f"wrote {len(items)} candidates to {out} {counts}")


def cmd_split(sources: list[Path], gold_dir: Path, seed: int) -> None:
    outs = [gold_dir / f"{name}.jsonl" for name in ("dev", "test")]
    if any(o.exists() for o in outs):
        # re-splitting would silently move verified items between splits
        raise SystemExit(f"{gold_dir} already has dev.jsonl or test.jsonl; refusing to re-split")
    items = split_items([i for src in sources for i in read_jsonl(src)], seed)
    for out, name in zip(outs, ("dev", "test"), strict=True):
        write_jsonl(out, [i for i in items if i.split == name])
    n_dev = sum(i.split == "dev" for i in items)
    print(f"wrote {n_dev} dev and {len(items) - n_dev} test items to {gold_dir}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.gold")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="multi hop and comparison candidates from the corpus manifest")
    b.add_argument("--raw", type=Path, default=RAW_HOTPOT)
    b.add_argument("--manifest", type=Path, default=FULL_MANIFEST)
    b.add_argument("--out", type=Path, default=GOLD_DIR / "candidates.jsonl")
    sp = sub.add_parser("split", help="dev and test files with the contract type mix")
    sp.add_argument(
        "--candidates",
        type=Path,
        nargs="+",
        default=[GOLD_DIR / "candidates.jsonl", GOLD_DIR / "single_hop.jsonl"],
    )
    sp.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    sp.add_argument("--seed", type=int, default=7)
    args = p.parse_args(argv)
    if args.cmd == "build":
        cmd_build(args.raw, args.manifest, args.out)
    elif args.cmd == "split":
        cmd_split(args.candidates, args.gold_dir, args.seed)


if __name__ == "__main__":
    main()
