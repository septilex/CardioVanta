# Design: R1 — Unified Feature & Outcome Contract

## Contract layout
File: `contracts/feature_schema.v2.json`, `contract_version` 2.0.0.

- `outcome`: the clinical outcome.
  - Definition: greater than 50% diameter stenosis in at least one major coronary vessel.
  - Positive: value 1, `disease_present`. Negative: value 0, `disease_absent`.
  - `output_probability`: "P(disease present)".
- `model_label_mappings.packages[]`: model-specific metadata only. The single entry is `cardiovanta-lr13@1.0.0` with `disease_present_label: 0` and `status: interim_legacy`. Future packages declare `outcome_semantics.disease_present_label` in their own metadata; the clinical outcome definition does not change for that.
- `features[]`, in `feature_order`:
  - All features: id, label, type, description, unit (with `unit_evidence`), required, missing_value_policy, evidence.
  - Continuous features add `accepted` and `development_range`.
    - `accepted`: `finite_only`, with no hard bounds, matching the backend.
    - `development_range`: a warning guardrail, equal to the ranges in `artifacts/model/feature_schema.json`.
  - Discrete features add `options[]`, each with `code`, `display_label`, `clinical_meaning` and `verification`.
- `verification_levels`:

  | Level | Applies to | Meaning in contract |
  |---|---|---|
  | `verified_patient_matched` | cp | clinical meaning asserted |
  | `codebook_and_project_contract` | sex, fbs, exang, restecg, ca 0–3 | clinical meaning asserted |
  | `unverified` | slope, thal 1–3 | legacy display labels; `clinical_meaning: null` |
  | `undefined_in_codebook` | ca 4, thal 0 | neutral display label; `clinical_meaning: null` |

## Generator
- Uses the standard library only.
- Validates strictly. Generation fails with exit code 2 on any of:
  - unknown keys or duplicate ids;
  - unsupported types or optional features;
  - verification status inconsistent with `clinical_meaning`;
  - binary codes other than [0, 1];
  - outcome-orientation errors.
- Output is rendered purely from the contract, in stable order (`pprint` / `json.dumps`), and written with LF line endings. Each file is headed with the contract version and the SHA-256 of the contract's canonical JSON.
- `--check` compares the rendered output with the files on disk, ignoring CRLF conversion, and exits 1 when they are stale.

## Integration
- **Backend:** `PredictRequest(ClinicalFeaturesBase)` keeps the same name, field order, `extra='forbid'`, `allow_inf_nan=False` and Literal codes. Tests compare it with a frozen copy of the pre-R1 class over a matrix of payloads and show identical behaviour.
- **Outcome module:** `src/inference/outcome.py` imports `OUTCOME_ID`, `PROBABILITY_DEFINITION` and `LEGACY_PACKAGE_DISEASE_LABELS` from the generated module, which is pure data and depends only on Pydantic. It never reads the JSON at runtime, so the Vercel bundle (`includeFiles`) is unchanged.
- **Frontend:** imports `CATEGORICAL_OPTIONS` and `CATEGORICAL_LABELS`. The option text is identical to the pre-R1 UI, so the appearance is unchanged.

## Risks
- **Hand-edited generated files:** caught by `--check` and by the R1 tests.
- **Unchecked TypeScript:** the generated TypeScript could not be type-checked locally (no `node_modules`). CI's `tsc --noEmit` is the gate.
