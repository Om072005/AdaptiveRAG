"""Fixtures shared across test folders."""

from typing import Any

import pytest


@pytest.fixture
def query_result() -> Any:
    """A QueryResult with a graph path, the same one the contract tests build."""
    from contract.test_query_response import result

    return result(with_graph=True)
