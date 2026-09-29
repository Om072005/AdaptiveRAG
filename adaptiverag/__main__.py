"""python -m adaptiverag ask "question" [--mode graph] | serve [--port 8000]"""

import argparse

import uvicorn

from adaptiverag.types import Mode


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="answer one question and print the trace id")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=["auto", "vector", "graph", "hybrid"], default="auto")
    serve = sub.add_parser("serve", help="run the local API for the local page")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.command == "serve":
        uvicorn.run("adaptiverag.server:app", host="127.0.0.1", port=args.port)
    else:
        ask_and_print(args.question, args.mode)


def ask_and_print(question: str, mode: Mode) -> None:
    from adaptiverag.pipeline import answer_query

    r = answer_query(question, mode, source="cli")
    print(f"answer: {r.answer.short}\n\n{r.answer.text}\n")
    for c in r.answer.citations:
        print(f"  [{c.n}] {c.title}  ({c.chunk_id})")
    print(f"\nroute {r.decision.final} | model {r.answer.model} ({r.answer.select_reason})")
    print(f"confidence {r.answer.confidence} | flagged {r.flagged}")
    print(f"cost ${r.total_cost_usd:.6f} | latency {r.total_latency_ms} ms")
    print(f"trace {r.trace_id}")


if __name__ == "__main__":
    main()
