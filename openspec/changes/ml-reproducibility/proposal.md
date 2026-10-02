# Proposal

## Why

The ML training process lacks definitive provenance tracing and relies on a hardcoded output directory, making verification and deterministic reproduction brittle. To ensure clinical safety and model reliability, we must produce exact metadata tying the artifacts to their exact dataset versions, code state, and environment, while allowing isolated runs to verify deterministic reproduction without risking overwriting the live production artifacts.

## What Changes

- Add a safe configurable `--output-dir` parameter to `src/experiment/phase5.py`.
- Enhance requirements parsing logic to robustly support utf-16/utf-8 files and isolate correct dependency versions.
- Generate a comprehensive provenance manifest in `metadata.json` including data SHA256 hashes, git commit, python version, dependencies, model configuration, split counts, and hashes of all generated artifacts.
- Implement isolated tests in `tests/test_phase5.py` that perform reproducibility verification inside temporary directories and prove deterministic equivalence.
- Ensure total preservation and freeze of the exact production artifact hashes.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

## Impact

- `src/experiment/phase5.py` (CLI interface and provenance packaging)
- `tests/test_phase5.py` (Test suite)
- `metadata.json` (Additional provenance schema fields appended on generation)
