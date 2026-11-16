"""
The model version the application serves by default, and the golden synthetic probabilities of every
registered version. Change SERVED_VERSION here (and in backend/app/core/config.py / .env.example) when
the served model changes; tests that check the served model read these values.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MODEL_ID = "cardiovanta-lr13"
SERVED_VERSION = "1.1.1"
SERVED_QUALIFIED_NAME = f"{MODEL_ID}@{SERVED_VERSION}"

ARTIFACT_DIRS = {
    "1.0.0": ROOT / "artifacts" / "model",
    "1.1.0": ROOT / "artifacts" / "model-1.1.0",
    "1.1.1": ROOT / "artifacts" / "model-1.1.1",
}
SERVED_ARTIFACT_DIR = ARTIFACT_DIRS[SERVED_VERSION]

# The scikit-learn (joblib) model whose fitted parameters the served model uses. Tests that recompute the
# probability independently with scikit-learn load this one; 1.1.1 is a portable export of 1.1.0.
SKLEARN_REFERENCE_VERSION = "1.1.0"
SKLEARN_REFERENCE_DIR = ARTIFACT_DIRS[SKLEARN_REFERENCE_VERSION]

# P(significant obstructive CAD present) for the synthetic HIGH / LOW fixtures.
# 1.1.0 (H2.1 pooled calibration) is less compressed toward 0.5 than 1.0.0; the ranking is unchanged.
GOLDEN = {
    "1.0.0": {"HIGH": 0.985790929, "LOW": 0.016065906},
    "1.1.0": {"HIGH": 0.994343297, "LOW": 0.007331075},
    "1.1.1": {"HIGH": 0.994343297, "LOW": 0.007331075},  # portable export of 1.1.0, identical predictions
}
SERVED_GOLDEN = GOLDEN[SERVED_VERSION]
