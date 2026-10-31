# Proposal: R2 — Modular ML Package & Versioned Model Registry

## Why
Before R2:
- ML inference lived in `src/inference/`, a namespace shared with the TypeScript frontend.
- The FastAPI backend owned model loading.
- Models were deserialized twice at startup (once by `ModelLoader`, once by `InferenceEngine.__init__`).
- No model was loaded with checksum verification. Hashes were checked only in CI.
- No explicit model identity, versioning, model card or machine-checkable outcome mapping existed.

## What Changes
- New installable package `cardiovanta_ml` (Python 3.11, `pip install ./cardiovanta_ml[test]`), independent of FastAPI and Next.js:
  - `contracts`: the canonical contract JSON (moved here byte-identically, read via `importlib.resources`) and the generated Pydantic module;
  - `inference`: predict, outcome and explain, ported unchanged;
  - `registry`: loader, metadata, integrity, exceptions, and the legacy validator.
- Versioned registry entry `artifacts/models/cardiovanta-lr13/1.0.0/` (`metadata.json`, `checksums.sha256`, `model_card.md`). It references the original, unmodified artifacts in `artifacts/model/`.
- `load_model(model_id, version, registry_root)`:
  - explicit selection only;
  - SHA-256 verification before deserialization;
  - strict metadata, contract and outcome-mapping validation;
  - post-load class, feature and association checks;
  - fail closed;
  - one load per process.
- FastAPI becomes an integration layer: startup calls the registry once, and the endpoint calls the package engine.
- Compatibility wrappers are retained at `src/inference/{predict,outcome}.py`, `backend/app/core/model_loader.py` and `backend/app/schemas/generated_features.py`.
- `vercel.json` `includeFiles` adds `cardiovanta_ml/**`, which is required for the function bundle to contain the package.

## Non-goals
- No retraining, recalibration or artifact modification.
- No change to features, codes, validation, outcome definition, disease orientation, or the `/api/v1/predict` request/response contract.
- No resolution of the unverified `slope`, `thal`, `ca=4` or `thal=0` meanings.
- No access to `heart.csv`, the 61 locked rows, or Phase 17 outputs.
