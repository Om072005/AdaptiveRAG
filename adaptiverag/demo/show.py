"""The terminal view of a live query: each step as it ends, then the model's reasoning and answer
as they stream. Fed by the trace listener (telemetry.trace.Listener)."""

import os
import sys
from typing import Any, TextIO

INDENT = " " * 15
SHOWN_SEEDS = 5  # a long question can match dozens of aliases
DIM, BOLD, RESET = "\x1b[2m", "\x1b[1m", "\x1b[0m"


def use_color(out: TextIO) -> bool:
    if os.environ.get("NO_COLOR") or not out.isatty():
        return False
    if sys.platform == "win32":
        os.system("")  # noqa: S605 S607 (an empty command turns on ANSI colors in the Windows console)
    return True


def seconds(ms: int | float) -> str:
    return f"{ms / 1000:.1f} s" if ms >= 1000 else f"{int(ms)} ms"


def describe(e: dict[str, Any]) -> list[str]:
    """The step as lines: a headline, then details indented under it."""
    step = e["step"]
    if step == "embed":
        cached = ", cached" if e["cached"] else ""
        return [f"{e['model']}, {e['dims']} dims{cached}  {seconds(e['ms'])}"]
    if step == "classify":
        trusted = "trusted" if e["confidence"] >= e["min_confidence"] else "below the bar"
        probs = "  ".join(
            f"{k} {v:.2f}" for k, v in sorted(e["probs"].items(), key=lambda p: -p[1])
        )
        return [
            f"{e['label']} {e['confidence']:.2f} ({e['method']}; {trusted} {e['min_confidence']})",
            probs,
        ]
    if step == "link":
        return [link_line(e["seeds"])]
    if step == "route":
        return [f"{e['initial']} (asked: {e['requested']})", *e["reasons"]]
    if step == "retrieve":
        return retrieve_lines(e)
    if step == "fallback":
        return [f"{e['why']}, so {e['to']}"]
    if step == "model":
        if e["model"] is None:
            return ["no chunks, so no model call: not enough context"]
        return [f"{e['size']} {e['model']}", e["reason"]]
    if step == "generated":
        where = f", {e['processor']}" if e["processor"] else ""
        cached = ", cached" if e["cached"] else ""
        return [
            f"{e['tokens_in']} in, {e['tokens_out']} out tokens, {seconds(e['ms'])}{where}{cached}"
        ]
    if step == "answer":
        flag = ", flagged for review" if e["flagged"] else ""
        cites = "  ".join(f"[{c['n']}] {c['title']}" for c in e["citations"])
        return [f"{e['short']}  (confidence {e['confidence']:.2f}{flag})", cites]
    if step == "cost":
        calls = ", ".join(f"{c['role']} {c['model']}" for c in e["calls"])
        return [
            f"${e['total_cost_usd']:.6f} in {seconds(e['total_latency_ms'])}",
            calls,
            f"trace {e['trace_id']}",
        ]
    return [str({k: v for k, v in e.items() if k not in ("type", "step", "at_ms")})]


def link_line(seeds: list[dict[str, Any]]) -> str:
    """Seeds by name, best first: entities that share a name (kept apart on purpose, such as two
    people called the same) show once with their count."""
    if not seeds:
        return "no entity found in the question"
    names: dict[str, tuple[float, int]] = {}
    for s in seeds:
        best, n = names.get(s["name"], (0.0, 0))
        names[s["name"]] = (max(best, s["score"]), n + 1)
    shown = [
        f"{name} {score:.2f}" + (f" ({n} entities)" if n > 1 else "")
        for name, (score, n) in list(names.items())[:SHOWN_SEEDS]
    ]
    if len(names) > SHOWN_SEEDS:
        shown.append(f"and {len(names) - SHOWN_SEEDS} more")
    return ", ".join(shown)


def retrieve_lines(e: dict[str, Any]) -> list[str]:
    head = f"{e['route']}: {len(e['hits'])} chunks, top {e['top_score']:.2f}"
    if e["route"] != "vector":
        head += ", path found" if e["path_found"] else ", no path"
    lines = [f"{head}  {seconds(e['ms'])}"]
    lines += [f"[{h['n']}] {h['title']}  {h['score']:.4f} {h['source']}" for h in e["hits"]]
    for p in e["paths"]:
        walk = " ".join(
            f"{s} -{pred}-> {o}" if i == 0 else f"-{pred}-> {o}"
            for i, (s, pred, o) in enumerate(p["edges"])
        )
        lines.append(f"path {p['score']:.2f}: {walk}")
    return lines


class LivePrinter:
    """Call it with each event; it prints as they come."""

    def __init__(self, out: TextIO = sys.stdout) -> None:
        self.out = out
        self.color = use_color(out)
        self.n = 0
        self.streaming: str | None = None  # the kind of text being streamed right now

    def paint(self, text: str, style: str) -> str:
        return f"{style}{text}{RESET}" if self.color else text

    def __call__(self, event: dict[str, Any]) -> None:
        if event["type"] == "delta":
            self.piece(event["kind"], event["text"])
            return
        self.end_stream()
        self.n += 1
        first, *rest = [line for line in describe(event) if line]
        self.out.write(f"{self.n:>3} {self.paint(event['step'].ljust(10), BOLD)} {first}\n")
        for line in rest:
            self.out.write(f"{INDENT}{line}\n")
        self.out.flush()

    def piece(self, kind: str, text: str) -> None:
        if kind != self.streaming:
            self.end_stream()
            self.out.write(f"    {self.paint(kind.ljust(10), DIM)} ")
            self.streaming = kind
        body = text.replace("\n", "\n" + INDENT)
        self.out.write(self.paint(body, DIM) if kind == "thinking" else body)
        self.out.flush()

    def end_stream(self) -> None:
        if self.streaming is not None:
            self.out.write("\n")
            self.streaming = None
