# Design

## Context

The current ML Phase 5 pipeline directly overwrites production artifacts when run, and generates limited provenance information. We need to freeze production artifacts, enable safe isolated validation runs, and ensure every generated artifact contains a cryptographic link back to its generating context.

## Goals / Non-Goals

**Goals:**
- Provide an isolated execution mode for Phase 5 (`--output-dir`).
- Generate complete provenance data (hashes, commit, versions) inside `metadata.json`.
- Ensure tests can verify determinism without affecting production.
- Keep the existing production artifacts 100% frozen.

**Non-Goals:**
- Modify the ML algorithm or methodology.
- Touch frontend or backend server code.

## Decisions

- **CLI Argument `--output-dir`**: We use `argparse` to allow overriding the target directory. If the provided directory resolves to the production `artifacts/model/` directory, the script throws an error unless run in explicit production mode.
- **Robust Requirements Parsing**: `requirements.txt` is encoded in `utf-16le` on Windows, leading to `UnicodeDecodeError`. The design reads bytes and attempts `utf-8` then `utf-16le` decoding to extract the `scikit-learn` version dynamically.
- **Provenance Manifest**: Added Git commit retrieval via `subprocess`, python version via `sys.version`, and cryptographic SHA256 hashes of the four output artifacts (`model.joblib`, `explanation_model.joblib`, `feature_schema.json`, `reference_predictions.csv`) which are embedded directly into `metadata.json`.

## Risks / Trade-offs

- **Risk:** Shell execution for `git rev-parse` fails.
  **Mitigation:** Wrapped in a `try...except` block, defaulting to `"unknown"` if git is unavailable.
