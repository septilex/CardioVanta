"""
The model version the application serves by default, and the golden synthetic probabilities of every
registered version. Change SERVED_VERSION here (and in backend/app/core/config.py / .env.example) when
the served model changes; tests that check the served model read these values.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MODEL_ID = "cardiovanta-lr13"
SERVED_VERSION = "1.1.0"
SERVED_QUALIFIED_NAME = f"{MODEL_ID}@{SERVED_VERSION}"

ARTIFACT_DIRS = {
    "1.0.0": ROOT / "artifacts" / "model",
    "1.1.0": ROOT / "artifacts" / "model-1.1.0",
}
SERVED_ARTIFACT_DIR = ARTIFACT_DIRS[SERVED_VERSION]

# P(significant obstructive CAD present) for the synthetic HIGH / LOW fixtures.
# 1.1.0 (H2.1 pooled calibration) is less compressed toward 0.5 than 1.0.0; the ranking is unchanged.
GOLDEN = {
    "1.0.0": {"HIGH": 0.985790929, "LOW": 0.016065906},
    "1.1.0": {"HIGH": 0.994343297, "LOW": 0.007331075},
}
SERVED_GOLDEN = GOLDEN[SERVED_VERSION]
