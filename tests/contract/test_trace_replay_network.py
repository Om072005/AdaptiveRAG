"""Stored answer traces replay through the serializer: valid, snippets capped, no secrets."""

import json
import re

import pytest

from adaptiverag.serialize import SNIPPET_CHARS, response_from_trace
from adaptiverag.stores.db import conn

pytestmark = pytest.mark.network

SECRET = re.compile(
    r"gsk_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_-]{20,}|AQ\.[0-9A-Za-z_.-]{20,}|postgres(ql)?://|Bearer "
)


def latest_answer_traces(n: int = 200) -> list[str]:
    with conn() as c:
        rows = c.execute(
            "select trace_id from traces where detail ? 'answer' and detail ? 'retrieval'"
            " order by created_at desc limit %s",
            (n,),
        ).fetchall()
    return [str(r[0]) for r in rows]


def test_latest_traces_replay_through_the_serializer() -> None:
    ids = latest_answer_traces()
    if not ids:
        pytest.skip("no answer traces on this branch yet")
    for trace_id in ids:
        body = response_from_trace(trace_id)
        assert body["trace_id"] == trace_id
        snippets = [h["snippet"] for h in body["retrieval"]["hits"]]
        snippets += [c["snippet"] for c in body["answer"]["citations"]]
        assert all(len(s) <= SNIPPET_CHARS for s in snippets)
        assert not SECRET.search(json.dumps(body)), f"secret-like text in trace {trace_id}"
