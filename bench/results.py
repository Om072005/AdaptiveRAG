"""Benchmark results: docs/results/<name>-<run_id>.md and .json, with git sha and config hash."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from adaptiverag.config import ROOT, config_hash

RESULTS_DIR = ROOT / "docs" / "results"


def git_state() -> tuple[str, bool]:
    """(HEAD sha, whether the working tree has uncommitted changes)."""
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    )
    return sha.stdout.strip(), bool(dirty.stdout.strip())


def new_run_id(label: str) -> str:
    """'{yyyymmdd-hhmm}-{label}', local time, the same clock as eval run ids."""
    return f"{datetime.now():%Y%m%d-%H%M}-{label}"


def write(
    name: str, run_id: str, params: dict[str, Any], rows: list[dict[str, Any]], md: str
) -> Path:
    """Write the json (every parameter) and the md (for people); returns the md path."""
    sha, dirty = git_state()
    record = {
        "run_id": run_id,
        "name": name,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_sha": sha,
        "git_dirty": dirty,
        "config_hash": config_hash(),
        "params": params,
        "rows": rows,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base = RESULTS_DIR / f"{name}-{run_id}"
    base.with_suffix(".json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    header = (
        f"Run `{run_id}` · {record['created_at']} · git `{sha[:12]}`{' (dirty)' if dirty else ''}"
        f" · config `{record['config_hash']}`\n\n"
    )
    base.with_suffix(".md").write_text(md.replace("{header}", header), encoding="utf-8")
    return base.with_suffix(".md")
