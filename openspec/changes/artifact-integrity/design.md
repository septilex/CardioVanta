# Design

## Context

We have established safe ML pipeline testing (Phase 5 reproducibility), but we must mathematically lock the resulting deployed model bundle.

## Goals / Non-Goals

**Goals:**
- Provide a machine-readable, deterministic SHA256 manifest of the expected production artifacts.
- Perform strict byte-for-byte SHA256 integrity verification during CI and test execution.
- Alert and block merges/deployments if artifacts change.

**Non-Goals:**
- Do not alter the actual artifacts in any way.
- Do not change ML behaviors.

## Decisions

- **Stable Hash Calculation:** The script will read files in raw binary mode (`rb`) and hash chunks to ensure the calculation is completely robust against CRLF/LF line-ending differences across environments or any textual encoding anomalies.
- **External Manifest:** We decouple the hashes from the code by placing them in `configs/artifact_hashes.json`. We will not use `metadata.json` for validation because it is a generated output meant to log provenance of the generated bundle, while this manifest serves as the *expected baseline* for the frozen bundle. Thus, no circular hash logic can occur.

## Risks / Trade-offs

- **Risk:** Cross-platform path resolution issues.
  **Mitigation:** We use `pathlib.Path` globally across the tests and the script.
