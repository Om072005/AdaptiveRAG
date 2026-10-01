"""Fixtures shared across test folders."""

from typing import Any

import pytest


@pytest.fixture
def query_result() -> Any:
    """A QueryResult with a graph path, the same one the contract tests build."""
    from contract.test_query_response import result

    return result(with_graph=True)


@pytest.fixture(autouse=True)
def local_models_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every configured local model counts as pulled and nothing asks the model server where a
    model is loaded, so no test depends on an Ollama running on the machine. Tests of
    llm.installed and llm.processor import the real functions at module load."""
    from adaptiverag import llm
    from adaptiverag.config import models

    roots = {llm._server_url(s) for s in models().values() if s.load_url}
    names = {s.model for s in models().values()}
    monkeypatch.setattr(llm, "_installed", {root: set(names) for root in roots})
    monkeypatch.setattr(llm, "processor", lambda spec: None)
