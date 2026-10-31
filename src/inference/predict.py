"""
Compatibility wrapper (R2). The implementation moved to ``cardiovanta_ml.inference``.

Pre-R2 callers (``scripts/detect_drift.py``, Phase 13 research scripts,
``tests/test_phase5.py``) construct ``InferenceEngine()`` with no arguments. This
wrapper keeps that working by loading the explicitly pinned production model
through the versioned, SHA-256-verified registry. It does not load artifacts
itself, and it does not pick a "latest" version.
"""
from pathlib import Path
from typing import Optional, Union

from cardiovanta_ml.inference.predict import InferenceEngine as _PackageInferenceEngine
from cardiovanta_ml.registry import load_model
from src.config.config import BASE_DIR

# Explicit pin for legacy no-argument callers. Keep in sync with backend settings MODEL_ID/MODEL_VERSION.
LEGACY_DEFAULT_MODEL_ID = "cardiovanta-lr13"
LEGACY_DEFAULT_MODEL_VERSION = "1.0.0"
REGISTRY_ROOT = BASE_DIR / "artifacts"


class InferenceEngine(_PackageInferenceEngine):
    def __init__(self, model_dir: Optional[Union[str, Path]] = None):
        loaded = load_model(LEGACY_DEFAULT_MODEL_ID, LEGACY_DEFAULT_MODEL_VERSION, registry_root=REGISTRY_ROOT)
        if model_dir is not None and Path(model_dir).resolve() != loaded.artifact_dir:
            raise ValueError(
                "InferenceEngine(model_dir=...) only accepts the registered artifact directory "
                f"{loaded.artifact_dir}; load other models with cardiovanta_ml.load_model(model_id, version, registry_root)."
            )
        super().__init__(loaded)


__all__ = ["InferenceEngine"]
