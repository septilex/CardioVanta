# Proposal: R1 — Unified Feature & Outcome Contract

## Why
CardioVanta's 13 production clinical inputs and the meanings of their categorical codes were hand-copied into at least five places: two JSON schemas, the Pydantic request model, the TypeScript types and the assessment UI's label tables. Nothing machine-checkable connected them, which is how the chest-pain labels and the outcome orientation drifted apart undetected (corrected in R0.3). The outcome semantics, meaning what the probability represents, were also not recorded anywhere machine-readable.

## What Changes
- Add `contracts/feature_schema.v2.json`, the single versioned source of truth for:
  - the 13 production inputs: types, units, accepted codes, development ranges, and code meanings with verification status and evidence;
  - the clinical outcome: P(significant obstructive CAD present).
- Keep artifact-specific model label mappings in a separate `model_label_mappings` section, distinct from the clinical outcome definition. The legacy package 1.0.0 maps disease to label 0.
- Add a deterministic, standard-library generator `contracts/codegen/generate.py` with a `--check` mode. It emits `backend/app/schemas/generated_features.py` (Pydantic v2) and `src/types/generated-features.ts`.
- Backend: `PredictRequest` and `FeatureContributions` inherit the generated bases, and `src/inference/outcome.py` reads the outcome and legacy-mapping constants from the generated module.
- Frontend: `src/types/index.ts` re-exports the generated types, and the assessment page's categorical selects render from the generated options.

## Non-goals
- No model change, retraining, recalibration or new API version. The `/api/v1/predict` request and response fields are unchanged; only descriptions change.
- No change to the 13-feature input schema or to the accepted codes.
- No resolution of the unverified `slope` and `thal` meanings; they remain explicitly unverified.
- No UI redesign.
