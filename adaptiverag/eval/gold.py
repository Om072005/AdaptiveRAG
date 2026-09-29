"""python -m adaptiverag.eval.gold build|generate|split|verify|replace|status (see main)"""

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from adaptiverag.config import ROOT, settings

GOLD_DIR = ROOT / "data" / "gold"
RAW_HOTPOT = ROOT / "data" / "raw" / "hotpot_dev_distractor_v1.json"
FULL_MANIFEST = ROOT / "data" / "corpus" / "full.json"
FULL_QUESTIONS = 300  # the full corpus size from contract section 4

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
    body = "".join(to_json(i) + "\n" for i in items)
    # an unchanged file is left alone: a Windows checkout has CRLF, and rewriting it with LF would
    # show it as modified in git and stop the next rebase
    if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") == body:
        return
    path.write_text(body, encoding="utf-8", newline="\n")


def split_items(candidates: list[GoldItem], seed: int = 7) -> list[GoldItem]:
    """Draw dev then test per type with a fixed seed; items not drawn are left out."""
    out = []
    for qtype in sorted(QTYPES):
        pool = seeded_pool(candidates, qtype, seed)
        need = SPLIT_MIX["dev"][qtype] + SPLIT_MIX["test"][qtype]
        if len(pool) < need:
            raise ValueError(f"{qtype}: {len(pool)} candidates, need {need}")
        n_dev = SPLIT_MIX["dev"][qtype]
        for i, item in enumerate(pool[:need]):
            item.split = "dev" if i < n_dev else "test"
            out.append(item)
    return sorted(out, key=lambda i: (i.split, i.id))


def seeded_pool(candidates: list[GoldItem], qtype: str, seed: int = 7) -> list[GoldItem]:
    """Candidates of one type in the order split_items draws them."""
    pool = sorted((c for c in candidates if c.type == qtype), key=lambda c: c.id)
    random.Random(f"{seed}:{qtype}").shuffle(pool)
    return pool


def replacement_for(
    item: GoldItem, candidates: list[GoldItem], used: set[str], seed: int = 7
) -> GoldItem:
    """The next candidate of the same type that no split uses, in the split's seeded order."""
    for c in seeded_pool(candidates, item.type, seed):
        if c.id not in used:
            return GoldItem(**{**asdict(c), "split": item.split, "verified_by": ""})
    raise SystemExit(f"no unused {item.type} candidate left to replace {item.id}")


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


def cmd_generate(n: int, temperature: float, out: Path) -> None:
    from adaptiverag import llm
    from adaptiverag.eval import single_hop
    from adaptiverag.ingest.loader import load_hotpot

    docs, _ = load_hotpot(FULL_QUESTIONS)
    items, rejects = single_hop.generate(single_hop.pick_documents(docs, n), llm.chat, temperature)
    write_jsonl(out, items)
    print(f"wrote {len(items)} single hop candidates to {out}, rejected {len(rejects)}")
    for doc_id, reason in rejects:
        print(f"  reject {doc_id}: {reason}")


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


def judge_subset(items: list[GoldItem], n: int, seed: int = 7) -> list[GoldItem]:
    """n items drawn per type in proportion to the split (largest remainder), in a seeded order.

    The judge's free quota cannot score every answer of every variant, so each judged run scores
    this same fixed subset; EM, F1 and recall still cover the whole split."""
    counts = {t: sum(i.type == t for i in items) for t in sorted(QTYPES)}
    exact = {t: n * c / len(items) for t, c in counts.items()}
    take = {t: int(v) for t, v in exact.items()}
    for t in sorted(exact, key=lambda t: (-(exact[t] - take[t]), t))[: n - sum(take.values())]:
        take[t] += 1
    picked = [i for t in sorted(QTYPES) for i in seeded_pool(items, t, seed)[: take[t]]]
    return sorted(picked, key=lambda i: i.id)


def cmd_subset(n: int, out: Path, seed: int) -> None:
    picked = judge_subset(load_split("dev"), n, seed)
    lines = [
        f"# The fixed {n} dev questions every judged run scores (eval.gold subset),",
        f"# drawn per type in proportion to the dev split, seed {seed}.",
        "# Use: eval.run --questions data/gold/judge_subset.toml --judge",
        "",
    ]
    for i in picked:
        lines += ["[[question]]", f'id = "{i.id}"', f'type = "{i.type}"', ""]
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    counts = {t: sum(i.type == t for i in picked) for t in sorted(QTYPES)}
    print(f"wrote {len(picked)} questions to {out} {counts}")


def cmd_replace(n: int, reason: str, gold_dir: Path, sources: list[Path]) -> None:
    from adaptiverag.eval import verify

    items = [i for _, i in verify.numbered(gold_dir)]
    if not 1 <= n <= len(items):
        raise SystemExit(f"item {n} is out of range 1..{len(items)}")
    log = gold_dir / "replaced.jsonl"
    removed = {i.id for i in read_jsonl(log)} if log.exists() else set()
    old = items[n - 1]
    candidates = [c for src in sources for c in read_jsonl(src)]
    new = replacement_for(old, candidates, {i.id for i in items} | removed)
    new.notes = f"replaces {old.id}: {reason}"
    items[n - 1] = new
    verify.save(gold_dir, items)
    # the removed item stays on record with its reason, it is never silently dropped
    note = f"replaced by {new.id}: {reason}"
    old.notes = f"{old.notes}; {note}" if old.notes else note
    with log.open("a", encoding="utf-8", newline="\n") as f:
        f.write(to_json(old) + "\n")
    print(f"#{n}: {old.id} replaced by {new.id} ({new.type}, {new.split}), not verified yet")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.gold")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="multi hop and comparison candidates from the corpus manifest")
    b.add_argument("--raw", type=Path, default=RAW_HOTPOT)
    b.add_argument("--manifest", type=Path, default=FULL_MANIFEST)
    b.add_argument("--out", type=Path, default=GOLD_DIR / "candidates.jsonl")
    g = sub.add_parser("generate", help="single hop candidates from corpus paragraphs")
    g.add_argument("--n", type=int, default=60)
    # the contract allows a non zero temperature here only, so questions vary across paragraphs
    g.add_argument("--temperature", type=float, default=0.7)
    g.add_argument("--out", type=Path, default=GOLD_DIR / "single_hop.jsonl")
    sp = sub.add_parser("split", help="dev and test files with the contract type mix")
    sp.add_argument(
        "--candidates",
        type=Path,
        nargs="+",
        default=[GOLD_DIR / "candidates.jsonl", GOLD_DIR / "single_hop.jsonl"],
    )
    sp.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    sp.add_argument("--seed", type=int, default=7)
    v = sub.add_parser("verify", help="walk items N..M (dev then test, 1 based) and verify each")
    v.add_argument("--from", dest="first", type=int, required=True)
    v.add_argument("--to", dest="last", type=int, required=True)
    v.add_argument("--reviewer", required=True)
    v.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    r = sub.add_parser("replace", help="swap item N for the next unused candidate of its type")
    r.add_argument("n", type=int)
    r.add_argument("--reason", required=True)
    r.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    r.add_argument(
        "--candidates",
        type=Path,
        nargs="+",
        default=[GOLD_DIR / "candidates.jsonl", GOLD_DIR / "single_hop.jsonl"],
    )
    su = sub.add_parser("subset", help="the fixed dev questions every judged run scores")
    su.add_argument("--n", type=int, default=40)
    su.add_argument("--seed", type=int, default=7)
    su.add_argument("--out", type=Path, default=GOLD_DIR / "judge_subset.toml")
    st = sub.add_parser("status", help="which items are not verified yet")
    st.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    args = p.parse_args(argv)
    if args.cmd in ("verify", "status"):
        from adaptiverag.eval import verify

        # a Windows console defaults to cp1252 and cannot print names like Pavic with its accent
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

    if args.cmd == "build":
        cmd_build(args.raw, args.manifest, args.out)
    elif args.cmd == "generate":
        cmd_generate(args.n, args.temperature, args.out)
    elif args.cmd == "split":
        cmd_split(args.candidates, args.gold_dir, args.seed)
    elif args.cmd == "verify":
        counts = verify.run(args.gold_dir, args.first, args.last, args.reviewer.strip().lower())
        print(f"verified {counts['y']}, flagged {counts['n']}, skipped {counts['s']}")
    elif args.cmd == "replace":
        cmd_replace(args.n, args.reason, args.gold_dir, args.candidates)
    elif args.cmd == "subset":
        cmd_subset(args.n, args.out, args.seed)
    elif args.cmd == "status":
        s = verify.status(args.gold_dir)
        print(f"{s['total']} items, {len(s['unverified'])} not verified: {s['unverified']}")
        for n, found in s["problems"].items():
            print(f"  #{n}: {', '.join(found)}")


if __name__ == "__main__":
    main()
