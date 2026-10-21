# Proposal

## Why

Extensive within-cohort benchmarking on the single-centre Cleveland development dataset ($N=242$)—spanning 97 model configurations, non-linear feature engineering (Phase 16), threshold tuning, and regularised discriminant analysis—indicates that single-centre discriminative accuracy plateaus at approximately 85.5% to 86.0%. More critically, high performance on a single historical cohort cannot evaluate clinical transportability or guard against geographic and institutional distribution shift; a formal multi-centre research study evaluating external generalisability across independent clinical centres is urgently required to measure true algorithmic transportability without claiming an unproven 90% accuracy ceiling.

## What Changes

- A new, strictly isolated multi-centre research initiative (Phase 17) investigating cross-centre transportability across three historical cohorts ($N=736$ total): Cleveland Development ($N=242$), Hungarian Institute of Cardiology in Budapest ($N=294$), and Long Beach VA Medical Center in California ($N=200$). Hungary and Long Beach are designated as external clinical centres relative to Cleveland.
- Explicit disclosure that the Cleveland development cohort has already been used extensively across prior CardioVanta phases (Phases 1–16); its held-out evaluation in this study measures consistency with prior development, not fresh independent confirmation.
- Exclusion of the Switzerland cohort ($N=123$) from the primary analysis because its extreme class imbalance (93.5% disease prevalence, only 8 non-diseased controls) makes specificity, calibration, and other diagnostic estimates statistically unstable, compounded by 100% missing cholesterol data. This exclusion is a methodological control for estimation variance and does not imply or prove that the model cannot work in that setting.
- Implementation of a strict Leave-One-Center-Out (LOCO) cross-validation scheme where all imputation, preprocessing, scaling, and calibration are fitted exclusively on training centres, guaranteeing that the held-out centre never influences fitting, hyperparameter choice, or model selection.
- Explicit resolution of the cross-centre missingness dilemma with rigorous feature counting:
  - Systematically excluding `ca`, `thal`, and `slope` leaves 10 clinical features (`age`, `sex`, `cp`, `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`).
  - The missing-aware pipeline incorporates fold-local median imputation on `chol` and adds the binary indicator `chol_is_missing`, producing **11 model inputs**.
  - The comparison pipeline completely removes `chol` (and `chol_is_missing`), retaining **9 clinical features** (and 9 model inputs).
- Clarification of clinical requirements: the 9-clinical-feature model retains fasting blood sugar (`fbs`); it eliminates the requirement for laboratory serum lipid testing (`chol`), but still requires glycemic status assessment (e.g. fasting glucose check or clinical history).
- Rigorous data validation contract and feature-specific sentinel conventions:
  - **Sequential Validation Contract**:
    1. Parse each source using its verified file format and attribute mapping.
    2. Normalize only confirmed missing-value sentinels using feature-specific and cohort-specific rules.
    3. Validate values against the documented feature domain and flag unexplained violations.
    4. Preserve legitimate zero values (`sex = 0` female, `fbs = 0` $\le 120$ mg/dl, `exang = 0` no angina, `restecg = 0` normal, `oldpeak = 0.0` normal isoelectric ST response, and disease-free label `target = 0`).
    5. Fit imputation, scaling, and calibration using training centres only.
  - **CP Category Coding**: The canonical UCI codebook documents `cp` values 1–4 (1 = typical angina, 2 = atypical angina, 3 = non-anginal pain, 4 = asymptomatic). Actual source files must be profiled during implementation; unexpected values must not be silently remapped or classified as missing without evidence. If a verified source variant uses 0–3 coding, an explicit mapping to the canonical schema will be documented.
  - **Sentinel `-9` Clarification**: The confirmed missing-value sentinel in primary UCI documentation is `"?"`. Candidate sentinels such as `"-9"` or `"-9.0"` are treated as unverified conventions requiring cohort- and feature-specific confirmation during implementation profiling rather than being universally applied.
  - **Provisional Cholesterol Zero Counts**: Literature-reported zero-cholesterol counts (~23 in Hungary, ~131 in Long Beach VA) are treated as provisional estimates to be confirmed against raw files upon download; no prior raw-file profiling is implied.
- Standardisation of feature units, categorical encodings, and binary target conversion ($num = 0 \implies 0$, $num \ge 1 \implies 1$).
- Independent reporting of held-out performance for Cleveland, Hungary, and Long Beach separately, reporting discrimination (ROC-AUC, PR-AUC), threshold-0.5 diagnostic metrics (accuracy, recall, specificity, precision, F1), and calibration metrics (Brier score, calibration curve).
- Explicit disclosure of uncertainty boundaries: patient-level bootstrap confidence intervals quantify sampling variation within each observed cohort, not variation across future unobserved hospitals; three historical centres provide inherently limited evidence regarding generalisation across broader healthcare institutions.
- Strict isolation and preservation of the locked 61-patient Cleveland test set: it will not be loaded, merged, preprocessed, or evaluated during any external training or model selection.
- Full compliance with the UCI Machine Learning Repository Creative Commons Attribution 4.0 International (CC BY 4.0) license and attribution requirements, noting explicitly that licensing compliance does not constitute clinical or regulatory approval.
- **BREAKING**: No production behavior, production APIs, runtime dependencies, or model artifacts (`artifacts/model/model.joblib`) will be modified. The research model is an exploratory benchmark and will not replace the production model.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None.

## Impact

- **Affected Code**: Creates dedicated research evaluation modules (e.g. `experiments/phase17_multicenter_validation.py`) and corresponding unit tests under `tests/`. All existing production code, inference pipelines, monitoring modules, and CLI endpoints remain completely untouched.
- **Production Safety**: The production model artifact (`artifacts/model/model.joblib`), pipeline configuration, and locked Cleveland test set ($N=61$) remain completely untouched and quarantined from external multi-centre workflows.
- **Data Lineage & Provenance**: Introduces reproducible loaders for raw UCI Hungarian (`hungarian.data`) and Long Beach VA (`long-beach-va.data`) cohorts alongside the existing Cleveland development split ($N=242$), with cryptographic SHA-256 integrity verification, licensed under CC BY 4.0.
- **Clinical Scope & Disclaimer**: Historical cohorts (collected 1984–1989) reflect referral populations undergoing cardiac catheterization and do not constitute prospective clinical validation in modern care pathways. Compliance with open-source licensing does not constitute regulatory or medical device approval. Findings will be published strictly as historical algorithmic transportability benchmarks.
