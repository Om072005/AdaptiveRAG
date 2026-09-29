"""Every name in contract section 3 exists where the contract says. Implementations may change,
names may not without an announcement."""

import importlib

import pytest

SURFACE = {
    "adaptiverag.config": ["settings", "models", "router_cfg", "ingest_cfg", "config_hash"],
    "adaptiverag.stores.db": ["conn"],
    "adaptiverag.stores.migrate": ["main"],
    "adaptiverag.llm": ["chat", "embed", "BudgetExceeded", "RateLimited"],
    "adaptiverag.telemetry.trace": ["Trace"],
    "adaptiverag.generate.prompts": ["build_prompt"],
    "adaptiverag.generate.cite": ["bind_citations"],
    "adaptiverag.generate.select": ["choose_model"],
    "adaptiverag.generate.confidence": ["answer_confidence"],
    "adaptiverag.generate.answer": ["synthesize"],
    "adaptiverag.pipeline": ["answer_query"],
    "adaptiverag.serialize": ["to_response", "response_from_trace"],
    "adaptiverag.ingest.loader": ["load_hotpot"],
    "adaptiverag.ingest.normalize": ["normalize", "doc_id"],
    "adaptiverag.ingest.chunking": [
        "split_sentences",
        "chunk_fixed",
        "chunk_sentence",
        "chunk_semantic",
    ],
    "adaptiverag.ingest.embed": ["embed_chunks"],
    "adaptiverag.stores.vector": ["search", "retrieve"],
    "adaptiverag.stores.flat": ["FlatIndex"],
    "adaptiverag.stores.hnsw": ["HNSW"],
    "adaptiverag.router.hybrid": ["rrf", "mmr", "merge_rerank"],
    "adaptiverag.telemetry.aggregate": ["economics"],
    "adaptiverag.ingest.extract": ["extract_triples"],
    "adaptiverag.ingest.validate": ["validate"],
    "adaptiverag.ingest.resolve": ["normalize_name", "blocking_key", "resolve"],
    "adaptiverag.stores.graph": ["link_entities", "traverse", "retrieve"],
    "adaptiverag.router.classify": ["features", "classify"],
    "adaptiverag.router.policy": ["decide_initial", "needs_fallback"],
    "adaptiverag.router.route": ["route_and_retrieve"],
    "adaptiverag.eval.metrics": [
        "normalize_answer",
        "em",
        "f1",
        "recall_at_k",
        "mrr",
        "sp_precision",
    ],
    "adaptiverag.eval.judge": ["judge"],
}


@pytest.mark.parametrize("module", sorted(SURFACE))
def test_contract_names_exist(module: str) -> None:
    mod = importlib.import_module(module)
    missing = [name for name in SURFACE[module] if not hasattr(mod, name)]
    assert not missing, f"{module} is missing {missing}"


def test_trace_methods_exist() -> None:
    from adaptiverag.telemetry.trace import Trace

    for name in ["span", "add_llm", "set", "save"]:
        assert callable(getattr(Trace, name))


def test_index_classes_have_contract_methods() -> None:
    from adaptiverag.stores.flat import FlatIndex
    from adaptiverag.stores.hnsw import HNSW

    assert all(hasattr(FlatIndex, m) for m in ["add", "search"])
    assert all(hasattr(HNSW, m) for m in ["add", "search", "save", "load"])
