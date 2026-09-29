"""python -m adaptiverag.ingest run --corpus mini|full [--strategies fixed,sentence,semantic]"""

import sys

from adaptiverag.ingest import pipeline

USAGE = "usage: python -m adaptiverag.ingest run --corpus mini|full [--strategies ...]"


def main(argv: list[str]) -> None:
    if argv[:1] == ["run"]:
        pipeline.main(argv[1:])
    else:
        raise SystemExit(USAGE)


if __name__ == "__main__":
    main(sys.argv[1:])
