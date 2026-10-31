"""
Compatibility wrapper (R2). The implementation moved to ``cardiovanta_ml.registry.legacy``.

The FastAPI app no longer uses ``ModelLoader``. Startup uses the versioned,
SHA-256-verified registry (``cardiovanta_ml.load_model``). This import path is
kept for existing callers and tests of the legacy package-directory validator.
"""
from cardiovanta_ml.registry.legacy import ModelLoader, ModelPackage

__all__ = ["ModelLoader", "ModelPackage"]
