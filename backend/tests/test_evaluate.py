"""Labeled evaluation of grounded commands against the thin baseline."""

from app.core.evaluate import run_evaluation


def test_grounded_predictions_match_hand_labeled_paths():
    report = run_evaluation()
    assert report["case_count"] == 6
    for case in report["cases"]:
        assert case["grounded"]["false_positives"] == []
        assert case["grounded"]["false_negatives"] == []


def test_thin_baseline_misses_domain_commands_and_mislabels_module():
    report = run_evaluation()
    health = next(case for case in report["cases"] if case["name"] == "health-service")
    assert health["thin"]["predicted"] == ["app start", "app status"]
    assert health["thin"]["false_positives"] == ["app status"]
    assert "health status" in health["thin"]["false_negatives"]
    assert report["grounded"]["recall"] == 1
    assert report["thin"]["recall"] < report["grounded"]["recall"]
    assert report["failure_cases"]
