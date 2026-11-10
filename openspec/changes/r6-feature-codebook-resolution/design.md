# Design: R6 — Clinical Feature Codebook Resolution

## Evidence hierarchy
Statuses may be upgraded only by evidence of level E1 or E2.

| Level | Evidence | Can verify a mapping? |
|---|---|---|
| E1 | Patient-level 1-to-1 matching between the training encoding and canonical UCI records, as done in Phase 17 for `cp` and `target` | Yes |
| E2 | A primary-source document that states the transformation explicitly (UCI documentation, or the dataset publisher's own description) | Yes |
| E3 | A codebook definition of the *canonical* codes only, without the transformation | No: it defines the source codes, not the mapping |
| E4 | Secondary or community claims, frequency similarity, model coefficients or feature importance | No. E4 items are recorded as hypotheses only |

## Sources (all read-only; no dataset rows are parsed)
- `data/external/raw/heart-disease.names`: the UCI attribute documentation (text). It is read as a document only; no dataset is parsed.
- `cardiovanta_ml/contracts/feature_schema.v2.json`: the current verification levels and accepted codes.
- `src/cardiovanta/data/validation.py`: the Phase 17 patient-matched `cp` mapping and domain definitions.
- `reports/phase17_multicenter_validation.md`: the Phase 17 matching protocol and target harmonisation.
- `reports/external_data_profiling.json`: documented sentinel counts for the external cohorts.
- Public documentation, retrieved 2026-10-31:
  - the UCI dataset page (loaded);
  - the Kaggle dataset page (HTTP 404).

## Decision rule
- A code's status changes only if E1 or E2 evidence for it exists in the sources above.
- Otherwise the status stays exactly as it is in the contract, with an explicit "unresolved" record that lists the evidence considered and the open path to resolution.

## Outputs
- `experiments/results/r6_codebook_evidence.json`, deterministic, and containing for each code:
  - the training (production) code;
  - the canonical UCI source code(s), if any;
  - the evidence items, each with its level;
  - the resolved status and confidence;
  - hypotheses, labelled as not evidence;
  - the resolution path.
- A consistency check: the status in the evidence record must equal the contract status, because the contract is not modified.
