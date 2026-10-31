"""
Compatibility re-export (R2). NOT a generated file, and holds no definitions.

The generated contract module moved into the ML package in R2:
    cardiovanta_ml/contracts/generated_features.py
(source: cardiovanta_ml/contracts/feature_schema.v2.json; regenerate with
``python contracts/codegen/generate.py``).

This module only keeps the R1 import path ``backend.app.schemas.generated_features``
working. Import from ``cardiovanta_ml.contracts.generated_features`` in new code.
"""
from cardiovanta_ml.contracts import generated_features as _generated
from cardiovanta_ml.contracts.generated_features import *  # noqa: F401,F403

__all__ = [name for name in dir(_generated) if not name.startswith("_")]
