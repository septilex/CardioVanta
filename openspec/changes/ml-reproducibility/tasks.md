# Tasks

## 1. Provenance and Isolation

- [x] 1.1 Implement `--output-dir` in `src/experiment/phase5.py` and verify it errors when targeting the production directory directly.
- [x] 1.2 Implement robust encoding detection (`utf-8`/`utf-16le`) for `requirements.txt` to safely parse dependency versions.
- [x] 1.3 Update the generated `metadata.json` to include git commit, python version, and exact SHA256 hashes for all output artifacts.

## 2. Testing and Validation

- [x] 2.1 Write `test_output_directory_isolation_and_provenance` in `tests/test_phase5.py` to run phase 5 in a temporary directory and verify the exact provenance fields are populated.
- [x] 2.2 Verify deterministic reproducibility by asserting exact dataframe equality between the newly generated `reference_predictions.csv` and the production version.
- [x] 2.3 Verify all tests pass (`pytest tests/`) explicitly in the Python 3.11 environment.
