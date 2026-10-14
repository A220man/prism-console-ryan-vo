"""HTTP create/read workflow against the FastAPI app."""

from fastapi.testclient import TestClient

from app.core.samples import SURFACE_SAMPLE
from app.core.version import read_version
from app.main import create_app


def _client(tmp_path):
    return TestClient(create_app(tmp_path / "prism.sqlite"))


def test_health_reads_version_file(tmp_path):
    client = _client(tmp_path)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": read_version()}


def test_create_then_read_round_trip(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/analyses", json=SURFACE_SAMPLE)
    assert created.status_code == 200
    body = created.json()
    assert body["id"] == 1
    assert body["grounded"]["commands"][0]["path"] == "notes create_note"
    assert body["created_at"].endswith("Z")
    fetched = client.get("/api/analyses/1")
    assert fetched.status_code == 200
    assert fetched.json()["grounded"]["executable"] == body["grounded"]["executable"]
    exported = client.get("/api/analyses/1/export")
    assert exported.status_code == 200
    assert exported.json()["commands"][0]["invocation"].startswith("lane_desk notes create_note")


def test_list_filters_pagination_and_persists_across_processes(tmp_path):
    client = _client(tmp_path)
    client.post("/api/analyses", json={"application": "ab_cd", "surfaces": []})
    client.post("/api/analyses", json={"application": "abXcd", "surfaces": []})
    client.post("/api/analyses", json={"application": "other", "surfaces": []})
    exact = client.get("/api/analyses", params={"application": "ab_cd"})
    assert exact.status_code == 200
    assert [item["application"] for item in exact.json()["items"]] == ["ab_cd"]
    page = client.get("/api/analyses", params={"limit": 1, "offset": 1})
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1
    again = TestClient(create_app(tmp_path / "prism.sqlite"))
    assert again.get("/api/analyses").json()["total"] == 3


def test_audit_records_create_and_export_without_source(tmp_path):
    client = _client(tmp_path)
    client.post(
        "/api/analyses",
        json={
            "application": "notes-app",
            "files": [{"path": "notes.py", "source": "def create_note(title):\n    return title\n"}],
        },
    )
    client.get("/api/analyses/1/export")
    audit = client.get("/api/audit")
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()["items"]]
    assert actions == ["analysis.exported", "analysis.created"]
    assert all("def create_note" not in item["detail"] for item in audit.json()["items"])


def test_missing_analysis_and_bad_inventory(tmp_path):
    client = _client(tmp_path)
    missing = client.get("/api/analyses/9")
    assert missing.status_code == 404
    assert missing.json()["error"] == "analysis not found"
    rejected = client.post("/api/analyses", json={"surfaces": []})
    assert rejected.status_code == 400
    assert rejected.json()["field"] == "application"
    invalid = client.get("/api/analyses", params={"limit": "many"})
    assert invalid.status_code == 422
    assert invalid.json()["error"] == "invalid request"
    out_of_range = client.get("/api/analyses", params={"limit": 0})
    assert out_of_range.status_code == 400


def test_sample_and_evaluation_endpoints(tmp_path):
    client = _client(tmp_path)
    sample = client.get("/api/sample")
    assert sample.json()["application"] == "lane-desk"
    python_sample = client.get("/api/sample", params={"kind": "python"})
    assert python_sample.json()["files"][0]["path"] == "notes.py"
    unknown = client.get("/api/sample", params={"kind": "binary"})
    assert unknown.status_code == 400
    evaluation = client.get("/api/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["grounded"]["recall"] == 1
    assert evaluation.json()["thin"]["recall"] < 1
