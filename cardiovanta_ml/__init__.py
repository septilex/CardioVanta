"""
cardiovanta_ml: CardioVanta's research ML core.

Responsibilities:
* ``cardiovanta_ml.contracts``: canonical clinical feature & outcome contract
  (bundled JSON and generated Pydantic definitions).
* ``cardiovanta_ml.registry``: versioned model registry. It selects a model by
  explicit ID and version, verifies SHA-256 checksums BEFORE deserialization, and
  validates metadata, outcome mapping and model compatibility (fails closed).
* ``cardiovanta_ml.inference``: prediction (P(disease present)), outcome
  orientation, and explanation of the explanation model.

This package does not depend on FastAPI or any frontend code. It is a research
tool and is not clinically validated.

Public API::

    from cardiovanta_ml import load_model, predict, explain, InferenceEngine
    model = load_model("cardiovanta-lr13", "1.0.0", registry_root="artifacts")
    result = predict({...13 features...}, model)

Attributes are imported lazily, so lightweight modules (for example the contract
hashing used by the code generator) can be imported without numpy or scikit-learn.
"""
from typing import Any

__version__ = "0.2.0"

_LAZY = {
    "load_model": ("cardiovanta_ml.registry.loader", "load_model"),
    "clear_model_cache": ("cardiovanta_ml.registry.loader", "clear_model_cache"),
    "LoadedModel": ("cardiovanta_ml.registry.loader", "LoadedModel"),
    "InferenceEngine": ("cardiovanta_ml.inference.predict", "InferenceEngine"),
    "predict": ("cardiovanta_ml.inference.predict", "predict"),
    "explain": ("cardiovanta_ml.inference.predict", "explain"),
    "RegistryError": ("cardiovanta_ml.registry.exceptions", "RegistryError"),
}

__all__ = ["__version__", *_LAZY]


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        import importlib

        module_name, attr = _LAZY[name]
        value = getattr(importlib.import_module(module_name), attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cardiovanta_ml' has no attribute {name!r}")
