"""python -m adaptiverag.router.train set              builds data/router/train.jsonl
python -m adaptiverag.router.train embed --slice K/N   embeds one slice of its questions
python -m adaptiverag.router.train rules             writes adaptiverag/router/weights/rules.json
python -m adaptiverag.router.train                   writes adaptiverag/router/weights/logreg.npz
python -m adaptiverag.router.train compare [--methods rules,logreg,llm]
                                                    writes docs/results/classifier-<run_id>.md

The set: bridge and comparison questions from seeded pages of the HotpotQA train split (Hugging Face
rows service, no download), plus single hop questions generated from train paragraphs that are not
in our corpus. Nothing in it may appear in the corpus or the gold set (tested).
"""

import argparse
import json
import random
import sys
from collections.abc import Callable
from statistics import median
from typing import Any

import httpx
import numpy as np

from adaptiverag import llm
from adaptiverag.config import ROOT, models, router_cfg
from adaptiverag.eval import single_hop
from adaptiverag.eval.report import confusion, macro_f1
from adaptiverag.ingest.loader import SOURCE, from_mirror_row
from adaptiverag.ingest.normalize import doc_id, join_sentences
from adaptiverag.ingest.pipeline import in_slice, parse_slice
from adaptiverag.router.classify import (
    RULES_CALIBRATION,
    WEIGHTS,
    classify,
    features,
    logreg_inputs,
    rule_bucket,
    rule_votes,
    softmax,
)
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Classification, Document, LLMResult
from bench import results

TRAIN_PATH = ROOT / "data" / "router" / "train.jsonl"
ROWS_URL = "https://datasets-server.huggingface.co/rows"
TRAIN_ROWS: dict[str, str | int] = {
    "dataset": "hotpotqa/hotpot_qa",
    "config": "distractor",
    "split": "train",
}
TRAIN_SOURCE = "hotpotqa-train"
LABELS = {"bridge": "multi_hop", "comparison": "comparison"}
# about 1,000 questions (agreed with the lead) in the gold set's mix of 40, 27 and 33 percent
MIX = {"multi_hop": 400, "comparison": 270, "single_hop": 330}
PAGE = 100
PAGES = 18  # comparisons are about a fifth of train, so 1,800 rows hold enough of them


def train_page(client: httpx.Client, offset: int, length: int) -> dict[str, Any]:
    response = client.get(ROWS_URL, params=TRAIN_ROWS | {"offset": offset, "length": length})
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


def fetch_rows(pages: int, seed: int) -> list[dict[str, Any]]:
    """Rows of seeded pages spread over the whole train split, in the original record layout."""
    with httpx.Client(timeout=60) as client:
        total = int(train_page(client, 0, 1)["num_rows_total"])
        starts = sorted(random.Random(seed).sample(range(0, total - PAGE, PAGE), pages))
        return [
            from_mirror_row(r["row"]) for s in starts for r in train_page(client, s, PAGE)["rows"]
        ]


def pick_questions(
    rows: list[dict[str, Any]], mix: dict[str, int], seed: int, banned: set[str]
) -> list[dict[str, str]]:
    """Bridge and comparison questions, a seeded choice per label, skipping banned texts."""
    pool = sorted(rows, key=lambda r: r["_id"])
    random.Random(seed).shuffle(pool)
    picked: list[dict[str, str]] = []
    for label in ("multi_hop", "comparison"):
        mine = [
            r
            for r in pool
            if LABELS.get(r["type"]) == label and r["question"].strip() not in banned
        ]
        picked += [
            {
                "id": f"hp_{r['_id']}",
                "question": r["question"].strip(),
                "label": label,
                "source": TRAIN_SOURCE,
            }
            for r in mine[: mix[label]]
        ]
    return picked


def paragraphs(rows: list[dict[str, Any]], corpus_doc_ids: set[str]) -> list[Document]:
    """Context paragraphs of the train rows as documents, leaving out any title our corpus holds."""
    docs: dict[str, Document] = {}
    for r in rows:
        for title, sentences in r["context"]:
            if doc_id(SOURCE, title) in corpus_doc_ids or title in docs:
                continue
            text, spans = join_sentences(sentences)
            docs[title] = Document(doc_id(TRAIN_SOURCE, title), TRAIN_SOURCE, title, text, spans)
    return list(docs.values())


def small_chat(role: str, messages: list[dict[str, str]], **kwargs: Any) -> LLMResult:
    """The gold generator asks for 'large'; training questions use the small model, whose own
    daily token quota covers a few hundred calls. Temperature 0, as everywhere but gold."""
    return llm.chat("small", messages, **{**kwargs, "temperature": 0.0})


def generate_single_hop(
    docs: list[Document], n: int, seed: int, chat: Callable[..., LLMResult] = small_chat
) -> tuple[list[dict[str, str]], list[tuple[str, str]]]:
    """n single hop questions from seeded paragraphs (the gold prompt and checks); one call each."""
    items, rejects = single_hop.generate(
        single_hop.pick_documents(docs, n + n // 10, seed), chat, 0.0
    )
    kept = [
        {
            "id": i.id,
            "question": i.question,
            "label": "single_hop",
            "source": "generated",
            "title": i.supporting_titles[0],
        }
        for i in items[:n]
    ]
    return kept, rejects


def build_set(seed: int = 7) -> None:
    corpus = json.loads((ROOT / "data" / "corpus" / "full.json").read_text(encoding="utf-8"))
    gold = [
        json.loads(line)
        for split in ("dev", "test")
        for line in (ROOT / "data" / "gold" / f"{split}.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    banned = {g["question"].strip() for g in gold}
    rows = [r for r in fetch_rows(PAGES, seed) if r["_id"] not in set(corpus["question_ids"])]
    print(f"train rows fetched: {len(rows)}")
    picked = pick_questions(rows, MIX, seed, banned)
    try:
        generated, rejects = generate_single_hop(
            paragraphs(rows, set(corpus["doc_ids"])), MIX["single_hop"], seed
        )
    except llm.RateLimited as e:
        # generated questions are cached, so a rerun after the reset continues where this stopped
        raise SystemExit(f"stopped by the provider quota ({e}); rerun later to resume") from e
    rows_out = sorted(picked + generated, key=lambda x: (x["label"], x["id"]))
    TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRAIN_PATH.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows_out), encoding="utf-8"
    )
    counts = {label: sum(x["label"] == label for x in rows_out) for label in MIX}
    print(f"wrote {len(rows_out)} questions to {TRAIN_PATH}: {counts}")
    print(f"generator rejects: {len(rejects)}")


CLASSES = ("single_hop", "multi_hop", "comparison")


def fit(
    x: np.ndarray, y: np.ndarray, lr: float, l2: float, epochs: int
) -> tuple[np.ndarray, np.ndarray]:
    """Multinomial logistic regression by full batch gradient descent from zero weights, so the
    same data always gives the same weights."""
    w = np.zeros((x.shape[1], len(CLASSES)))
    b = np.zeros(len(CLASSES))
    target = np.eye(len(CLASSES))[y]
    for _ in range(epochs):
        grad = (softmax(x @ w + b) - target) / len(x)
        w -= lr * (x.T @ grad + l2 * w)
        b -= lr * grad.sum(axis=0)
    return w.astype(np.float32), b.astype(np.float32)


def read_set() -> list[dict[str, str]]:
    lines = TRAIN_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def embed_slice(k: int, n: int) -> None:
    """Embed slice k of n of the training questions into the cache; a rerun skips what is done."""
    mine = [q["question"] for q in read_set() if in_slice(q["question"], k, n)]
    print(f"training embeddings slice {k}/{n}: {len(mine)} questions")
    try:
        llm.embed(mine, kind="query")
    except llm.RateLimited as e:
        raise SystemExit(f"slice {k}/{n} stopped by the quota ({e}); rerun later") from e
    print(f"training embeddings slice {k}/{n}: all {len(mine)} embedded or already cached")


def train_logreg() -> None:
    """Fit on the whole training set (never on dev or test) and write the weights file."""
    cfg = router_cfg()["classifier"]
    items = read_set()
    try:
        vecs = llm.embed([q["question"] for q in items], kind="query")
    except llm.RateLimited as e:
        raise SystemExit(
            f"embeddings stopped by the quota ({e}); fill them with embed slices"
        ) from e
    x = np.stack([logreg_inputs(q["question"], v) for q, v in zip(items, vecs, strict=True)])
    y = np.array([CLASSES.index(q["label"]) for q in items])
    w, b = fit(x, y, float(cfg["learning_rate"]), float(cfg["l2"]), int(cfg["epochs"]))
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    np.savez(WEIGHTS, W=w, b=b, labels=np.array(CLASSES), embed_model=models()["embed"].model)
    accuracy = float((np.argmax(x @ w + b, axis=1) == y).mean())
    print(f"trained on {len(items)} questions, training accuracy {accuracy:.4f}; wrote {WEIGHTS}")


def calibrate_rules(items: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    """For each bucket of the rules (winning label, lead in votes), how many training questions
    carry each true label."""
    buckets: dict[str, dict[str, int]] = {}
    for q in items:
        label, margin = rule_bucket(rule_votes(features(q["question"])))
        row = buckets.setdefault(f"{label} {margin}", {lb: 0 for lb in CLASSES})
        row[q["label"]] += 1
    return dict(sorted(buckets.items()))


def train_rules() -> None:
    """Count the buckets on the whole training set (never on dev or test); needs no quota."""
    items = read_set()
    buckets = calibrate_rules(items)
    out = {"source": "data/router/train.jsonl", "questions": len(items), "buckets": buckets}
    RULES_CALIBRATION.parent.mkdir(parents=True, exist_ok=True)
    RULES_CALIBRATION.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    right = sum(row[key.split()[0]] for key, row in buckets.items())
    print(
        f"rules label {right} of {len(items)} training questions right; wrote {RULES_CALIBRATION}"
    )
    for key, row in buckets.items():
        print(f"  {key}: {row}")


DEV_PATH = ROOT / "data" / "gold" / "dev.jsonl"
METHODS = ("rules", "logreg", "llm")


def label_f1(matrix: list[list[int]]) -> list[float]:
    """F1 per label, gold as rows; a label never predicted nor present scores 0."""
    out = []
    for i in range(len(matrix)):
        predicted = sum(row[i] for row in matrix)
        actual = sum(matrix[i])
        out.append(2 * matrix[i][i] / (predicted + actual) if predicted + actual else 0.0)
    return out


def score(items: list[dict[str, Any]], preds: list[Classification]) -> dict[str, Any]:
    """Macro F1 (the eval report's), F1 per label, cost and latency of one method on the items."""
    rows = [
        {"gold_type": q["type"], "predicted_type": p.label}
        for q, p in zip(items, preds, strict=True)
    ]
    conf = confusion(rows)
    if conf is None:
        raise ValueError("no predictions to score")
    return {
        "macro_f1": macro_f1(conf["matrix"]),
        "f1_by_label": dict(zip(conf["labels"], label_f1(conf["matrix"]), strict=True)),
        "matrix": conf["matrix"],
        "cost_per_query_usd": sum(p.cost_usd for p in preds) / len(preds),
        "p50_ms": median(p.latency_ms for p in preds),
    }


def compare_md(run_id: str, items: list[dict[str, Any]], scores: dict[str, dict[str, Any]]) -> str:
    """The comparison page for people; results.write fills in {header}."""
    counts = ", ".join(f"{sum(q['type'] == t for q in items)} {t}" for t in CLASSES)
    lines = [
        f"# Classifier comparison, dev split ({run_id})",
        "",
        f"{{header}}{len(items)} dev questions ({counts}), each labelled by every method. Rules and"
        " the logistic regression are trained on data/router/train.jsonl only. Latency is the"
        " classifier alone: the logistic regression reuses the query embedding retrieval computes"
        " anyway, and a cached model call keeps the latency recorded when it was first made. Cost"
        " is at list price.",
        "",
        "| Method | Macro F1 | " + " | ".join(f"F1 {t}" for t in CLASSES) + " | Cost per query USD"
        " | p50 ms |",
        "|---|---|" + "---|" * len(CLASSES) + "---|---|",
    ]
    for method, s in scores.items():
        f1s = " | ".join(f"{s['f1_by_label'][t]:.4f}" for t in CLASSES)
        lines.append(
            f"| {method} | {s['macro_f1']:.4f} | {f1s} | {s['cost_per_query_usd']:.8f}"
            f" | {s['p50_ms']:g} |"
        )
    for method, s in scores.items():
        lines += ["", f"{method}, gold as rows, predicted as columns:", ""]
        lines += ["| | " + " | ".join(CLASSES) + " |", "|---|" + "---|" * len(CLASSES)]
        lines += [
            f"| {t} | " + " | ".join(str(n) for n in row) + " |"
            for t, row in zip(CLASSES, s["matrix"], strict=True)
        ]
    return "\n".join([*lines, ""])


def compare(methods: list[str]) -> None:
    """Every method on the dev questions (never test). All three write the result file; fewer
    print a preview only, since the report compares all three."""
    items = [json.loads(line) for line in DEV_PATH.read_text(encoding="utf-8").splitlines() if line]
    questions = [q["question"] for q in items]
    vecs = np.zeros((len(items), models()["embed"].dims or 768), dtype=np.float32)
    if "logreg" in methods:
        try:
            vecs = llm.embed(questions, kind="query")
        except llm.RateLimited as e:
            raise SystemExit(f"dev question embeddings stopped by the quota ({e})") from e
    scores = {}
    for method in methods:
        preds = [
            classify(q, v, Trace(q, "auto", "cli"), method)
            for q, v in zip(questions, vecs, strict=True)
        ]
        scores[method] = score(items, preds)
        print(f"{method}: macro F1 {scores[method]['macro_f1']:.4f}")
    if sorted(methods) != sorted(METHODS):
        print("preview only: the report is written when all three methods run")
        return
    run_id = results.new_run_id("dev")
    rows = [
        {"method": m} | {k: s[k] for k in ("macro_f1", "cost_per_query_usd", "p50_ms")}
        for m, s in scores.items()
    ]
    params = {"split": "dev", "questions": len(items), "scores": scores}
    path = results.write("classifier", run_id, params, rows, compare_md(run_id, items, scores))
    print(f"wrote {path}")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.router.train")
    parser.add_argument("command", nargs="?", choices=["set", "embed", "rules", "compare"])
    parser.add_argument("--slice", type=parse_slice, default="1/1", help="K/N, for embed")
    parser.add_argument(
        "--methods", default=",".join(METHODS), help="for compare, for example rules,llm"
    )
    args = parser.parse_args(argv)
    if args.command == "set":
        build_set()
    elif args.command == "embed":
        embed_slice(*args.slice)
    elif args.command == "rules":
        train_rules()
    elif args.command == "compare":
        compare([m for m in args.methods.split(",") if m])
    else:
        train_logreg()


if __name__ == "__main__":
    main()
