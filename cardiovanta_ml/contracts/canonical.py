"""Canonical hashing of the clinical contract (standard library only).

Shared by the package (registry compatibility checks) and the code generator
(``contracts/codegen/generate.py``), so both compute the same digest.
"""
import hashlib
import json
from typing import Any


def contract_sha256(contract: Any) -> str:
    """SHA-256 of the canonical JSON form (independent of whitespace, key order and line endings)."""
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()
