import pytest

from adaptiverag.ingest import __main__ as cli
from adaptiverag.ingest import graph_cli, pipeline


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, list[str]]]:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(pipeline, "main", lambda argv: seen.append(("run", argv)))
    monkeypatch.setattr(graph_cli, "main", lambda argv: seen.append(("graph", argv)))
    return seen


def test_run_and_graph_get_the_rest_of_the_arguments(calls: list[tuple[str, list[str]]]) -> None:
    cli.main(["run", "--corpus", "mini"])
    cli.main(["graph", "--corpus", "mini", "--limit", "8"])
    assert calls == [("run", ["--corpus", "mini"]), ("graph", ["--corpus", "mini", "--limit", "8"])]


@pytest.mark.parametrize("argv", [[], ["ingest"], ["--corpus", "mini"]])
def test_anything_else_prints_the_usage(
    calls: list[tuple[str, list[str]]], argv: list[str]
) -> None:
    with pytest.raises(SystemExit, match="usage"):
        cli.main(argv)
    assert calls == []
