"""Scoring a pasted command list against a saved analysis."""

from fastapi.testclient import TestClient

from app.core.evaluate import score_proposal
from app.core.samples import SURFACE_SAMPLE
from app.main import create_app


def _client(tmp_path):
    return TestClient(create_app(tmp_path / "prism.sqlite"))


def test_score_proposal_ignores_argv_and_counts_precision_recall():
    commands = [
        {"path": "notes create_note", "executable": True},
        {"path": "notes search_notes", "executable": True},
        {"path": "notes broken", "executable": False},
    ]
    scored = score_proposal(
        [
            "notes create_note --title hi",
            "notes search_notes",
            "notes export",
            "notes search_notes",
        ],
        commands,
    )
    assert scored["true_positives"] == 2
    assert scored["precision"] == 0.666667
    assert scored["recall"] == 1.0
    assert scored["missed"] == []
    assert scored["unexpected"] == ["notes export"]


def test_score_proposal_rejects_non_string_entries():
    commands = [{"path": "app start", "executable": True}]
    try:
        score_proposal(["app start", 7], commands)
    except Exception as exc:  # CatalogError
        assert "commands must be a list of strings" in str(exc)
    else:
        raise AssertionError("expected CatalogError")


def test_score_endpoint_scores_against_saved_analysis(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/analyses", json=SURFACE_SAMPLE)
    analysis_id = created.json()["id"]

    response = client.post(
        f"/api/analyses/{analysis_id}/score",
        json={"commands": ["notes create_note --title x", "orders list_orders"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert body["true_positives"] == 2
    assert body["precision"] == 1.0
    assert body["recall"] == round(2 / 6, 6)
    assert "notes search_notes" in body["missed"]

    missing = client.post(f"/api/analyses/{analysis_id + 99}/score", json={"commands": []})
    assert missing.status_code == 404
