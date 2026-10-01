"""python -m adaptiverag demo setup | check | eval | page | stop | export

Runs the showcase from a fresh clone: an embedded Postgres under .demo/, the corpus from
data/demo/corpus.jsonl.gz embedded by your own Ollama, and every model on your machine."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import psycopg
from pgvector.psycopg import register_vector

from adaptiverag import llm
from adaptiverag.config import ROOT, models, settings
from adaptiverag.demo import corpus as demo_corpus
from adaptiverag.demo.show import LivePrinter
from adaptiverag.eval import metrics
from adaptiverag.eval.run import NEON_MAIN_HOST_PREFIX
from adaptiverag.stores import db, embedded, graph, migrate

REPLAYS = ROOT / "web" / "public" / "data" / "replays"
# one recorded question per type that the served route answered correctly
EVAL_QUESTIONS = (
    "sh_4272d4fe2120a996_1",  # single hop: When was Dwell magazine launched?
    "hp_5a8bae135542996e8ac889b6",  # multi hop: Nathan Bridger ... which actor?
    "hp_5a79332555429907847277e7",  # comparison: Who died first, Bryce Courtenay or Onetti?
)
REQUIRED_ROLES = ("embed", "small", "classify")  # large and judge are optional
API = "http://127.0.0.1:8000"
PAGE_PORT = 5173  # the API allows this origin (server.LOCAL_PAGE_ORIGINS)


def where() -> str:
    """Which database this command uses, said plainly."""
    configured = settings().database_url
    if configured in ("", db.EMBEDDED):
        return f"embedded Postgres in {embedded.PGDATA.relative_to(ROOT)}"
    return f"DATABASE_URL ({urlparse(configured).hostname})"


def progress(what: str, done: int, total: int) -> None:
    end = "\n" if done >= total else ""
    print(f"\r  embedding {what:<9} {done:>6} / {total}", end=end, flush=True)


def require_models(roles: tuple[str, ...]) -> None:
    missing = [models()[r].model for r in roles if not llm.installed(models()[r])]  # type: ignore[index]
    if missing:
        pulls = "\n".join(f"  ollama pull {m}" for m in sorted(set(missing)))
        raise SystemExit(f"Ollama is not running or lacks a model this needs:\n{pulls}")


# --- setup ---------------------------------------------------------------------------------


def setup(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    print(f"database   {where()}")
    require_models(("embed",))
    url = db.url()
    applied = migrate.apply(url)
    print(f"schema     {'applied ' + ', '.join(applied) if applied else 'up to date'}")
    data = demo_corpus.read_corpus()
    counts = data.meta["counts"]
    print(
        f"corpus     {data.meta['content']}: " + ", ".join(f"{v} {k}s" for k, v in counts.items())
    )
    with psycopg.connect(url, autocommit=True) as c:
        register_vector(c)
        demo_corpus.load_rows(c, data)
        demo_corpus.embed_missing(c, data, progress)
        have, missing = demo_corpus.table_counts(c), demo_corpus.missing_vectors(c)
    graph.forget_aliases()
    if have != counts or any(missing.values()):
        raise SystemExit(f"setup incomplete: rows {have}, rows without a vector {missing}")
    took = time.perf_counter() - started
    print(f"ready      in {took:.0f} s; next: python -m adaptiverag demo check")


# --- check ---------------------------------------------------------------------------------


def check_db() -> bool:
    try:
        with db.conn() as c:
            have, missing = demo_corpus.table_counts(c), demo_corpus.missing_vectors(c)
            trgm = graph.has_trgm(c)
    except Exception as e:  # any failure to reach it is the finding here
        print(f"database   {where()}: not reachable ({e})")
        return False
    want = demo_corpus.read_corpus().meta["counts"]
    loaded = have == want and not any(missing.values())
    matcher = "pg_trgm" if trgm else "Python word similarity (no pg_trgm)"
    state = "corpus loaded" if loaded else "run demo setup"
    print(f"database   {where()}: {state}; aliases by {matcher}")
    return loaded


def check_models() -> bool:
    ok = True
    for role, spec in models().items():
        have = llm.installed(spec)
        need = role in REQUIRED_ROLES
        ok &= have or not need
        state = "installed" if have else f"missing: ollama pull {spec.model}"
        note = "" if need else " (optional)"
        print(f"model      {role:<9}{spec.model:<20}{state}{note}")
    return ok


def check_gpu() -> None:
    smi = shutil.which("nvidia-smi")
    if smi is None:
        print("gpu        no NVIDIA GPU tool found: Ollama runs the models on what it finds")
        return
    query = "--query-gpu=name,memory.used,memory.total"
    out = subprocess.run([smi, query, "--format=csv,noheader"], capture_output=True, text=True)
    for line in out.stdout.strip().splitlines():
        print(f"gpu        {line.strip()}")


def warm_small() -> None:
    spec = models()["small"]
    started = time.perf_counter()
    try:
        llm.load_local(spec)
    except llm.RateLimited as e:
        print(f"warm       {spec.model}: {e}")
        return
    where_ = llm.processor(spec) or "loaded"
    print(f"warm       {spec.model} ready in {time.perf_counter() - started:.1f} s, {where_}")


def check(args: argparse.Namespace) -> None:
    ok = check_db()
    ok &= check_models()
    check_gpu()
    if ok:
        warm_small()
    try:
        health = httpx.get(f"{API}/api/health", timeout=2.0).json()
        print(f"api        {API} up, db {health['db']}")
    except (httpx.HTTPError, ValueError):
        print("api        not running (python -m adaptiverag demo page starts it)")
    if not ok:
        raise SystemExit(1)
    print('check      ok: python -m adaptiverag ask "When was Dwell magazine launched?"')


# --- eval ----------------------------------------------------------------------------------


def recorded(question_id: str) -> dict[str, Any]:
    replay = json.loads((REPLAYS / f"{question_id}.json").read_text(encoding="utf-8"))
    auto = replay["runs"]["auto"]
    r = auto["response"]
    return {
        "question": replay["question"],
        "type": replay["type"],
        "gold": replay["gold_answer"],
        "route": r["route"]["final"],
        "answer": r["answer"]["short"],
        "model": r["answer"]["model"],
        "f1": float(auto["metrics"]["f1"]),
        "cost": float(r["trace"]["cost"]["total"]),
    }


def refuse_team_main() -> None:
    host = urlparse(settings().database_url).hostname or ""
    if host.startswith(NEON_MAIN_HOST_PREFIX):
        raise SystemExit("demo eval never runs on the team's Neon main; unset DATABASE_URL")


def eval_one(i: int, rec: dict[str, Any], quiet: bool) -> dict[str, Any]:
    from adaptiverag.pipeline import answer_query

    print(f"\nquestion {i}/{len(EVAL_QUESTIONS)} ({rec['type']}): {rec['question']}")
    print(f"gold       {rec['gold']}")
    with llm.fresh():  # a live run every time, never an answer from the cache
        r = answer_query(
            rec["question"], "auto", source="eval", listener=None if quiet else LivePrinter()
        )
    return {
        "route": r.decision.final,
        "answer": r.answer.short,
        "model": r.answer.model,
        "f1": metrics.f1(r.answer.short, rec["gold"]),
        "cost": r.total_cost_usd,
    }


def eval_cmd(args: argparse.Namespace) -> None:
    refuse_team_main()
    require_models(REQUIRED_ROLES)
    print(f"database   {where()}; nothing is pinned, every trace stays in this database")
    rows = []
    for i, qid in enumerate(EVAL_QUESTIONS, 1):
        rec = recorded(qid)
        rows.append((rec, eval_one(i, rec, args.quiet)))
    print(
        "\n   type        route yours/recorded   F1 yours/recorded   cost yours/recorded   answer"
    )
    for rec, yours in rows:
        print(
            f"   {rec['type']:<11} {yours['route']:>7} / {rec['route']:<11} "
            f"{yours['f1']:>5.2f} / {rec['f1']:<10.2f} "
            f"${yours['cost']:.6f} / ${rec['cost']:<10.6f} {yours['answer']}"
        )
    mean = sum(y["f1"] for _, y in rows) / len(rows)
    print(f"\nmean F1    {mean:.2f} (recorded {sum(r['f1'] for r, _ in rows) / len(rows):.2f})")


# --- page ----------------------------------------------------------------------------------


def npm() -> str:
    found = shutil.which("npm")
    if found is None:
        raise SystemExit("npm not found: install Node.js 20 or newer to run the page")
    return found


def start_page() -> subprocess.Popen[bytes]:
    web = ROOT / "web"
    if not (web / "node_modules").exists():
        print("page       installing the page's packages (npm ci, once)")
        subprocess.run([npm(), "ci", "--silent"], cwd=web, check=True)
    env = {**os.environ, "VITE_LIVE_API_URL": API}
    cmd = [npm(), "run", "dev", "--", "--port", str(PAGE_PORT), "--strictPort"]
    return subprocess.Popen(cmd, cwd=web, env=env)


def page(args: argparse.Namespace) -> None:
    import uvicorn

    require_models(REQUIRED_ROLES)
    db.url()  # start the embedded database before the API takes requests
    os.environ["ADAPTIVERAG_SHOW_STEPS"] = "1"  # read when uvicorn imports the server below
    vite = start_page()
    print(f"page       http://localhost:{PAGE_PORT}  (the live question box is in chapter 03)")
    print(f"api        {API}/api/health; every step of each question prints below")
    try:
        uvicorn.run("adaptiverag.server:app", host="127.0.0.1", port=8000, log_level="warning")
    finally:
        stop_tree(vite)


def stop_tree(proc: subprocess.Popen[bytes]) -> None:
    """Stop the page server and its children: on Windows npm runs through a .cmd wrapper, and
    terminating the wrapper alone would leave Node holding the port."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.terminate()
    proc.wait(timeout=10)


# --- stop and export -----------------------------------------------------------------------


def stop(args: argparse.Namespace) -> None:
    print(
        "stopped the embedded database"
        if embedded.stop()
        else "the embedded database was not running"
    )


def export(args: argparse.Namespace) -> None:
    """Team only: write data/demo/corpus.jsonl.gz from the configured database."""
    if settings().database_url in ("", db.EMBEDDED):
        raise SystemExit("export reads the team database: set DATABASE_URL to Neon main")
    require_models(("embed",))
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    with db.conn() as c:
        data = demo_corpus.export(c, sha, progress)
    out = Path(args.out)
    demo_corpus.write_corpus(out, data)
    print(json.dumps(data.meta, indent=2))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="python -m adaptiverag demo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="create the embedded database and load the corpus (once)")
    sub.add_parser("check", help="database, models, GPU and API, then warm the small model")
    ev = sub.add_parser("eval", help="three recorded questions, live, next to the recorded runs")
    ev.add_argument("--quiet", action="store_true", help="only the table, not every step")
    sub.add_parser("page", help="the API plus the local page with the live question box")
    sub.add_parser("stop", help="stop the embedded database (its data stays)")
    ex = sub.add_parser("export", help="team only: write the corpus file from Neon main")
    ex.add_argument("--out", default=str(demo_corpus.CORPUS_FILE))
    args = parser.parse_args(argv)
    commands = {
        "setup": setup,
        "check": check,
        "eval": eval_cmd,
        "page": page,
        "stop": stop,
        "export": export,
    }
    commands[args.command](args)
