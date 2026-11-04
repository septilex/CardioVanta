"""
Prediction availability switch (Phase 10 production-incident containment).

Why it exists
-------------
On 2026-11-03 the live deployment was verified to return the inverted probability
(``docs/reports/PRODUCTION_VERIFICATION_2026-11-03.md``). Until a corrected deployment has been
verified, a deployment of this code must not generate any risk estimate.

How it works
------------
The single switch is the committed file ``configs/prediction_service.json``. This module (the API)
and ``src/lib/predictionAvailability.ts`` (the web app) both read it, so the two halves of one
deployment always agree.

It is deliberately **not** an environment variable: production settings cannot re-enable
predictions. Re-enabling is a reviewed change of ``predictions_enabled`` to ``true``, followed by a
verified deployment.

Fail-safe: predictions are enabled only when the file is readable, parses as a JSON object and
``predictions_enabled`` is exactly ``true``. Anything else keeps them unavailable.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

AVAILABILITY_FILE = Path(__file__).resolve().parents[3] / "configs" / "prediction_service.json"
UNAVAILABLE_CODE = "predictions_temporarily_unavailable"
DEFAULT_NOTICE = (
    "CardioVanta predictions are temporarily unavailable while we verify the prediction service. "
    "No risk estimate can currently be generated."
)


@dataclass(frozen=True)
class PredictionAvailability:
    enabled: bool
    notice: str


def load_prediction_availability(path: Path = AVAILABILITY_FILE) -> PredictionAvailability:
    """Read the switch. Any problem with the file means "unavailable" (fail-safe)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # unreadable, missing or malformed: stay unavailable
        logger.error(
            "Prediction availability file unreadable; predictions stay unavailable",
            extra={"error_type": type(exc).__name__},
        )
        return PredictionAvailability(enabled=False, notice=DEFAULT_NOTICE)
    if not isinstance(data, dict):
        return PredictionAvailability(enabled=False, notice=DEFAULT_NOTICE)
    notice = data.get("notice")
    if not isinstance(notice, str) or not notice.strip():
        notice = DEFAULT_NOTICE
    return PredictionAvailability(enabled=data.get("predictions_enabled") is True, notice=notice.strip())


# Read once per process: a deployment's switch never changes while it runs.
_AVAILABILITY = load_prediction_availability()


def current_availability() -> PredictionAvailability:
    return _AVAILABILITY


class PredictionsUnavailableError(Exception):
    """Raised before any request parsing or model call while predictions are unavailable."""

    def __init__(self, notice: str):
        super().__init__(notice)
        self.notice = notice


def require_predictions_available() -> None:
    """Route dependency for every prediction-producing endpoint."""
    availability = current_availability()
    if not availability.enabled:
        raise PredictionsUnavailableError(availability.notice)


def unavailable_body(notice: str) -> dict:
    """The structured 503 body. ``detail`` stays a string, as for every other API error."""
    return {"detail": notice, "code": UNAVAILABLE_CODE, "predictions_available": False}
