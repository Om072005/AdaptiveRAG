import importlib

import adaptiverag

SUBPACKAGES = ["ingest", "stores", "router", "generate", "eval", "telemetry"]


def test_version_is_set() -> None:
    assert adaptiverag.__version__


def test_every_subpackage_imports() -> None:
    for name in SUBPACKAGES:
        importlib.import_module(f"adaptiverag.{name}")
