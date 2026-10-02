# Proposal

## Why

The current deployment checks merely verify if the six ML artifact files exist. This provides no protection against silent tampering, drift, or unintended regenerations. We need an authoritative cryptographically enforced manifest that guarantees the production artifacts deployed exactly match the approved `v1.0.0` outputs.

## What Changes

- Create a strict manifest `configs/artifact_hashes.json` containing the approved SHA256 hashes of the six production artifacts.
- Introduce `scripts/verify_artifact_integrity.py` to calculate raw bytes hashes of the artifacts and assert they match the manifest.
- Embed this integrity verifier directly into the `.github/workflows/verify.yml` CI pipeline to fail the build if any artifact hash drifts.

## Capabilities

### New Capabilities
None

### Modified Capabilities
None

## Impact

- `.github/workflows/verify.yml`
- New: `configs/artifact_hashes.json`
- New: `scripts/verify_artifact_integrity.py`
- New: `tests/test_artifact_integrity.py`
