# Tasks

## 1. Core Logic

- [x] 1.1 Create `configs/artifact_hashes.json` with the approved SHA256 hashes for the six production artifacts.
- [x] 1.2 Create `scripts/verify_artifact_integrity.py` to compute SHA256 hashes and validate them against the manifest.
- [x] 1.3 Add tests to `tests/test_artifact_integrity.py` covering pass, fail (modified), and fail (missing) scenarios.

## 2. CI Integration

- [x] 2.1 Update `.github/workflows/verify.yml` to replace naive `test -f` checks with a direct call to `python scripts/verify_artifact_integrity.py`.
- [ ] 2.2 Run the script locally and confirm all 6 files pass without errors.
