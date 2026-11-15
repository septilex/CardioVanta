# Categorical Encoding Verification (2026-11-15, contract 2.1.0)

> **Result: three form inputs were mislabelled.** The training data (`data/raw/heart.csv`, the Kaggle
> re-encoding of UCI Cleveland) orders the codes of `restecg`, `slope` and `thal` differently from the UCI
> codebook. Contract 2.0.0 labelled them from the codebook or from legacy UI labels, so the option a person
> picked was sent to the model as a different finding. The model, its artifacts and every code value are
> unchanged; only the display labels, option order and form defaults changed.

## Method

- Source: UCI `heart+disease.zip` (`https://archive.ics.uci.edu/static/public/45/heart+disease.zip`), SHA-256
  `b17cd273da9ce1caa4710fce80227ea454d4dbf9fcbc8e6a9121672751563adc`, the value already pinned in
  `src/cardiovanta/data/external_loader.py`. File used: `processed.cleveland.data` (303 records).
- Rows: the 242 development rows only (`data/processed/dev_indices.json`, via `parse_cleveland_dev_cohort`).
  The 61 locked rows were not used.
- Matching key: `age, sex, trestbps, chol, thalach, oldpeak`. Every development row matched exactly one UCI
  record (242/242), and every training code maps to exactly one UCI code.
- Reproduce: `python scripts/research/verify_categorical_encoding.py PATH/TO/heart+disease.zip` (exit 0 = all
  mappings one-to-one).

## Results

| Input | Training code → UCI code (rows) | Contract 2.0.0 label | Verified label (2.1.0) |
|---|---|---|---|
| `cp` | 0→4 (115), 1→2 (41), 2→3 (71), 3→1 (15) | correct (Phase 17) | unchanged |
| `restecg` | 0→2 (114), 1→0 (124), 2→1 (4) | 0 Normal, 1 ST-T, 2 LVH | **0 LVH, 1 Normal, 2 ST-T** |
| `slope` | 0→3 (17), 1→2 (108), 2→1 (117) | 0 Upsloping, 1 Flat, 2 Downsloping | **0 Downsloping, 1 Flat, 2 Upsloping** |
| `thal` | 0→missing (1), 1→6 (14), 2→3 (129), 3→7 (98) | 0 "Code 0", 1 Normal, 2 Fixed | **0 Not recorded, 1 Fixed, 2 Normal, 3 Reversible** |
| `ca` | 0-3 identical; 4→missing (5) | 4 "Code 4" | **4 Not recorded** |
| `fbs`, `exang`, outcome | identical | correct | unchanged |

The outcome check (training disease label vs UCI `num > 0`, 242/242 agreement) independently confirms the
R0.3 orientation fix.

## Effect on predictions (production model `cardiovanta-lr13@1.0.0`)

| Profile | What the person chose | Old labels sent | Estimate shown | Correct estimate |
|---|---|---|---|---|
| Age 50, non-anginal pain, normal vitals | Normal ECG, upsloping ST, normal thallium | LVH, downsloping, fixed defect | 15.5% | **4.8%** |
| Age 62, asymptomatic, exercise angina, 2 vessels | LVH, downsloping, fixed defect | ST-T, upsloping, normal | 83.1% | **93.7%** |

Low-risk people were shown roughly three times their modelled risk, and some high-risk people were under-estimated.

## Changes

- `cardiovanta_ml/contracts/feature_schema.v2.json`: version 2.1.0; patient-matched labels, meanings and
  `canonical_uci_code` for `restecg`, `slope` and `thal`; `ca = 4` and `thal = 0` labelled "Not recorded".
  Generated Python/TypeScript regenerated. Registry metadata of `cardiovanta-lr13@1.0.0` now references
  contract 2.1.0 (SHA-256 `a548a9b7…`); the model artifacts and their checksums are untouched.
- Form: options listed in clinical order (normal finding first); "Not recorded" codes not offered; defaults are a
  normal resting ECG, upsloping ST segment, normal thallium scan and no ST depression.
- Tests pin the verified mapping (`backend/tests/test_r1_feature_contract.py`,
  `__tests__/encoding-and-coldstart.test.tsx`). Golden probabilities are unchanged.
