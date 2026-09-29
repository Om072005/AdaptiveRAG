"""python -m adaptiverag.ingest run --corpus mini|full [--strategies ...] | graph --corpus ..."""

import sys

from adaptiverag.ingest import graph_cli, pipeline

USAGE = (
    "usage: python -m adaptiverag.ingest run --corpus mini|full [--strategies ...]\n"
    "       python -m adaptiverag.ingest graph --corpus mini|full [...]"
)


def main(argv: list[str]) -> None:
    command, rest = (argv[0], argv[1:]) if argv else ("", [])
    if command == "run":
        pipeline.main(rest)
    elif command == "graph":
        graph_cli.main(rest)
    else:
        raise SystemExit(USAGE)


if __name__ == "__main__":
    main(sys.argv[1:])
