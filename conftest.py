"""
Shared pytest configuration.

Prediction containment (Phase 10). The shipped switch ``configs/prediction_service.json`` makes
``POST /api/v1/predict`` return 503. The existing serving tests verify prediction behaviour itself
(golden values, outcome orientation, validation, explanations, telemetry), so they run with the gate
opened in-process only; their assertions are unchanged. Tests marked ``prediction_containment``
(``backend/tests/test_prediction_containment.py``) see the real, shipped switch.

Nothing here reads environment variables or files: no setting can open the gate outside a test process.
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "prediction_containment: use the real, shipped prediction-availability switch (gate not opened)",
    )


@pytest.fixture(autouse=True)
def _open_prediction_gate_for_serving_tests(request, monkeypatch):
    if request.node.get_closest_marker("prediction_containment") is None:
        from backend.app.core import prediction_availability as pa

        monkeypatch.setattr(
            pa, "current_availability", lambda: pa.PredictionAvailability(enabled=True, notice=pa.DEFAULT_NOTICE)
        )
    yield
