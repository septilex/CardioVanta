"""
Clinical feature & outcome contract.

``feature_schema.v2.json`` in this directory is the single canonical contract.
It is shipped as package data and read with ``importlib.resources``, so it is
available after installation regardless of the working directory.

``generated_features.py`` is GENERATED from it by ``contracts/codegen/generate.py``
(repository tooling). Never edit it by hand.
"""
import json
from importlib import resources
from typing import Any, Dict

from cardiovanta_ml.contracts.canonical import contract_sha256

CONTRACT_RESOURCE = "feature_schema.v2.json"


def read_contract_text() -> str:
    """Raw text of the bundled canonical contract."""
    return resources.files(__name__).joinpath(CONTRACT_RESOURCE).read_text(encoding="utf-8")


def load_contract() -> Dict[str, Any]:
    """Parsed bundled canonical contract."""
    return json.loads(read_contract_text())


def bundled_contract_sha256() -> str:
    """Canonical SHA-256 of the bundled contract (compare with generated ``CONTRACT_SHA256``)."""
    return contract_sha256(load_contract())


__all__ = ["CONTRACT_RESOURCE", "read_contract_text", "load_contract", "bundled_contract_sha256", "contract_sha256"]
