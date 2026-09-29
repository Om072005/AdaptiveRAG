"""python -m adaptiverag ask "question" [--mode graph] | serve [--port 8000]"""

import argparse

import uvicorn


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
        raise SystemExit("ask arrives with the baseline pipeline (D3)")


if __name__ == "__main__":
    main()
