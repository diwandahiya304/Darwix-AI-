"""FastAPI wiring smoke test: exercises the real app (lifespan startup,
routes, request/response models, error handling) against whatever is
currently in data/processed/kb_records.jsonl — i.e. the real ingested KB,
same as kb/tests/test_pipeline_smoke.py's relationship to the ingestion
side. Deeper retrieval-quality checks belong in kb/eval/ (make kb-eval)
and kb/tests/test_search_integration.py, not here; this only checks that
the API layer itself is wired correctly.

Requires `make ingest-kb` to have been run at least once (skipped
otherwise, rather than failing, since a bare checkout has no
data/processed/kb_records.jsonl yet).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from kb.app.main import app
from kb.app.settings import REPO_ROOT

_KB_RECORDS_PATH = REPO_ROOT / "data" / "processed" / "kb_records.jsonl"

pytestmark = pytest.mark.skipif(
    not _KB_RECORDS_PATH.exists(),
    reason="No ingested KB yet — run `make ingest-kb` first.",
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_ready_with_indexed_records(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["records_indexed"] > 0


def test_search_returns_grounded_result_for_an_in_scope_query(client: TestClient):
    response = client.post("/search", json={"query": "can I add my spouse to the policy", "top_k": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["results"]
    assert "spouse" in body["results"][0]["content"].lower()
    assert body["results"][0]["citation"].startswith("[kb_")


def test_get_record_by_id_round_trips_from_search(client: TestClient):
    search_response = client.post("/search", json={"query": "waiting period pre-existing disease", "top_k": 1})
    record_id = search_response.json()["results"][0]["record_id"]

    record_response = client.get(f"/record/{record_id}")
    assert record_response.status_code == 200
    assert record_response.json()["record_id"] == record_id


def test_get_record_missing_id_returns_404(client: TestClient):
    response = client.get("/record/kb_does_not_exist_000")
    assert response.status_code == 404
