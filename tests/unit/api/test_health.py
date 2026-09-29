import pytest
from fastapi.testclient import TestClient

from adaptiverag import server
from adaptiverag.config import models

client = TestClient(server.app)


def test_health_reports_models_and_db_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "db_ok", lambda: False)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["db"] is False
    assert body["models"] == {role: spec.model for role, spec in models().items()}


def test_unknown_route_uses_the_error_shape() -> None:
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not Found", "fields": None}}


def test_local_page_origin_is_allowed() -> None:
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.network
def test_health_says_db_true_against_neon() -> None:
    assert client.get("/api/health").json()["db"] is True
