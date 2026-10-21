# Design

## Context

Previous extensive benchmarking on the single-centre Cleveland development dataset ($N=242$) across 97 model configurations, non-linear feature engineering (Phase 16), threshold tuning, and regularised discriminant analysis established that Cleveland development accuracy is bounded at approximately 85.5% to 86.0%. More importantly, single-cohort performance cannot establish clinical transportability or detect vulnerabilities to institutional distribution shift. Phase 17 investigates external generalisability by expanding the research benchmark across three independent historical clinical centres: Cleveland Clinic Foundation, Hungarian Institute of Cardiology in Budapest, and Veterans Administration Medical Center in Long Beach, California. See `proposal.md` for motivation and scope.

## Goals / Non-Goals

**Goals:**
- Design a rigorous Leave-One-Center-Out (LOCO) cross-validation framework across three independent centres ($N=736$ total patients) with complete mathematical isolation between training centres and held-out validation centres.
- Resolve the critical cross-centre missingness dilemma by directly benchmarking an 11-input missing-aware pipeline (10 clinical features + missingness indicator) against a 9-input non-invasive pipeline (9 clinical features, omitting `chol`).
- Establish a rigorous 5-step data validation contract: parse verified formats, normalize only confirmed sentinels, validate against documented domains, preserve legitimate zero values, and fit all transformers strictly on training centres.
- Specify canonical UCI chest pain (`cp`) coding (values 1–4) with implementation-time profiling and explicit remapping for verified source variants, prohibiting silent remapping or ad-hoc missingness classification.
- Treat `-9` / `-9.0` as an unverified candidate sentinel requiring implementation confirmation rather than a universal missingness rule across all features and cohorts.
- Designate literature-reported zero-cholesterol counts as provisional until confirmed on downloaded raw files.
- Report evaluation metrics—discrimination (ROC-AUC, PR-AUC), threshold-0.5 diagnostic performance (accuracy, recall, specificity, precision, F1), calibration quality (Brier score, calibration curve), and patient-level bootstrap confidence intervals—individually for each held-out centre.
- Explicitly disclose the status of each held-out centre: Hungary and Long Beach as external validation cohorts, and Cleveland as a retrospective development baseline rather than fresh independent confirmation.
- Clarify uncertainty boundaries: patient-level bootstrap intervals reflect within-cohort sampling variance, while three centres provide limited empirical evidence about broader healthcare system generalisation.
- Preserve the 61-sample locked Cleveland test set in strict quarantine, guaranteeing zero leakage into external training, preprocessing, or model selection.
- Enforce strict dataset provenance, cryptographic SHA-256 verification, and compliance with the UCI CC BY 4.0 license, while clarifying that licensing does not constitute clinical or regulatory approval.

**Non-Goals:**
- Replacing or modifying the deployed 13-feature Cleveland production model artifact (`artifacts/model/model.joblib`).
- Downloading external datasets or running machine learning experiments during this proposal phase.
- Claiming that retrospective 1980s referral cohorts constitute prospective clinical validation for contemporary medical practice.
- Asserting an unproven 90% cross-centre accuracy ceiling or manipulating evaluation protocols to achieve arbitrary targets.
- Evaluating the Switzerland cohort ($N=123$) in the primary multi-centre benchmark due to pathological missingness and severe metric instability.

## Decisions

### 1. Cohort Selection: 3-Centre Triangulation with Methodological Switzerland Exclusion

- **Included Centres ($N=736$ Total)**:
  1. **Cleveland Development Cohort** ($N=242$, Cleveland Clinic Foundation, OH; Dr. Robert Detrano). Represents the familiar baseline development cohort. *Critical Disclosure*: This cohort has been studied extensively across Phases 1–16; its held-out LOCO fold evaluates retrospective consistency with prior development, not fresh independent confirmation.
  2. **Hungarian Cohort** ($N=294$, Hungarian Institute of Cardiology, Budapest; Dr. Andras Janosi, `hungarian.data`). Represents an external European cardiology referral population with moderate missingness in lab assays.
  3. **Long Beach VA Cohort** ($N=200$, V.A. Medical Center, Long Beach, CA; Dr. Robert Detrano, `long-beach-va.data`). Represents an external US military veteran population with severe missingness in invasive and biochemical tests.

- **Excluded Centre: Switzerland Cohort ($N=123$, University Hospital, Zurich; Dr. William Steinbrunn, `switzerland.data`)**:
  - *Rationale*:
    - **Extreme Class Imbalance (93.5% Disease Prevalence)**: 115 of 123 patients have angiographically confirmed disease, leaving only 8 non-diseased controls. This severe skew makes specificity, false positive rate, and calibration estimates statistically unstable (a single misclassification shifts specificity by 12.5 percentage points, yielding a 95% confidence interval spanning over 30 percentage points).
    - **100% Missing Cholesterol**: Serum cholesterol (`chol`) is unrecorded (`0` or `?`) across all 123 patients, making any model relying on lipid measurements completely undefined without massive synthetic imputation.
    - **Severe Multimodal Missingness**: Resting ECG (`restecg`), fluoroscopy (`ca`), and thallium (`thal`) exhibit >95% missingness.
  - *Methodological Clarification*: Excluding Switzerland from the primary benchmark is a deliberate design control to prevent unstable metric estimation; it does *not* prove or imply that the underlying model cannot function or predict in that clinical setting, nor does it justify altering the defined 3-centre research scope.

### 2. Feature Schema, Consistent Feature Counts, and Fasting Blood Sugar Requirements

Non-Cleveland centres exhibit pervasive missingness in specialized or invasive procedures:
- Fluoroscopy vessels (`ca`): 98.6% missing in Hungary, 99.0% in Long Beach. Dropped from all multi-centre models.
- Thallium scintigraphy (`thal`): 90.5% missing in Hungary, 83.0% in Long Beach. Dropped from all multi-centre models.
- ST segment slope (`slope`): 48.0% missing in Hungary, 64.5% in Long Beach. Dropped from all multi-centre models.

Removing `ca`, `thal`, and `slope` from the original 13 UCI attributes leaves **10 clinical features**:
`age`, `sex`, `cp`, `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`.

This defines the two competing architectures:
- **Candidate A: Missing-Aware 10-Clinical-Feature Model (11 Model Inputs)**:
  - Clinical Features (10): `age`, `sex`, `cp`, `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`.
  - Handling of `chol` (0% missing in Cleveland, 7.8% provisional in Hungary, 65.5% provisional in Long Beach): Fold-local median imputation paired with a binary missingness indicator column (`chol_is_missing = 1` if `chol` was unphysiological `0` or confirmed missing sentinel).
  - Total Model Inputs: **11 input features** fed into the estimator pipeline (10 clinical features + 1 missingness indicator).
- **Candidate B: Non-Invasive 9-Clinical-Feature Model (9 Model Inputs)**:
  - Clinical Features (9): `age`, `sex`, `cp`, `trestbps`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`.
  - Handling of `chol`: Entirely omitted from the feature matrix and pipeline.
  - Total Model Inputs: **9 input features** fed into the estimator pipeline.
  - *Clinical Requirement Clarification for Fasting Blood Sugar (`fbs`)*: Candidate B eliminates the requirement for specialized laboratory serum lipid testing (`chol`). However, because it retains `fbs` (fasting blood sugar > 120 mg/dl), it does **not** eliminate all blood assessment. The `fbs` feature represents a glycemic check (such as prior patient history, chart review, or capillary/venous glucose screening). The clinical advantage of Candidate B is the elimination of specialized venous lipid panel turnaround, not the complete absence of glycemic assessment.
- **Decision Rule**:
  - If Candidate B (9 clinical features, 9 inputs) achieves macro-averaged held-out ROC-AUC and recall within 0.01 of Candidate A (10 clinical features, 11 inputs), Candidate B will be preferred on parsimony grounds due to its independence from laboratory lipid measurement.

### 3. Data Sentinel Standards, CP Coding & Validation Contract

#### A. The Global Zero Prohibition
**Zero is NEVER globally interpreted as missing.**
Globally replacing `0` with NaN would corrupt valid clinical measurements and binary categories:
- `sex = 0` indicates Female (valid binary category).
- `oldpeak = 0.0` indicates 0.0 mm ST segment depression during stress testing (a completely normal, healthy, and highly prevalent physiological measurement).
- `fbs = 0` indicates Fasting Blood Sugar $\le 120$ mg/dl (valid non-elevated glycemic status).
- `exang = 0` indicates No Exercise-Induced Angina (valid binary category).
- `restecg = 0` indicates Normal Resting Electrocardiogram (valid baseline category).
- `target = 0` indicates Absence of Significant Coronary Artery Disease (valid disease-free control label).

#### B. Documented UCI Feature Domains and Sentinel Specifications

| Attribute # | Standard Name | Documented Canonical UCI Domain | Valid Zero Status | Confirmed Missing Sentinels | Candidate Sentinels to Verify During Implementation | Domain Validation & Action |
|---|---|---|---|---|---|---|
| 1 | `age` | Integer / Continuous years $\ge 18$ | Invalid ($\le 0$ unphysiological) | `"?"` (raw text) | `"-9"`, `"-9.0"` | Values $\le 0$ or confirmed sentinels $\to$ `NaN`; flag unexpected strings |
| 2 | `sex` | Binary: 1 = Male, 0 = Female | **Valid (0 = Female)** | `"?"` (raw text) | `"-9"`, `"-9.0"` | **Preserve 0**; confirmed sentinels $\to$ `NaN`; flag values $\notin \{0, 1\}$ |
| 3 | `cp` | Discrete: 1 = Typical, 2 = Atypical, 3 = Non-anginal, 4 = Asymptomatic | Invalid (in canonical 1–4) | `"?"` (raw text) | `"-9"`, `"-9.0"` | Profile raw coding; if verified 0–3, map explicitly: $0 \to 1, 1 \to 2, 2 \to 3, 3 \to 4$; flag values $\notin \{1, 2, 3, 4\}$ |
| 4 | `trestbps` | Continuous mm Hg resting systolic BP ($\sim 80–220$) | Invalid (BP $\le 0$ non-viable) | `"?"`, `0` | `"-9"`, `"-9.0"` | Values $\le 0$ or confirmed sentinels $\to$ `NaN`; flag values $< 50$ or $> 250$ |
| 5 | `chol` | Continuous mg/dl serum cholesterol ($\sim 100–600$) | Invalid (chol $\le 0$ non-viable) | `"?"`, `0`, `0.0` | `"-9"`, `"-9.0"` | Values $\le 0$ or confirmed sentinels $\to$ `NaN`; provisional zero counts: Hungary (~23), Long Beach (~131) |
| 6 | `fbs` | Binary: 1 = True ($> 120$ mg/dl), 0 = False | **Valid (0 = Normal $\le 120$)** | `"?"` (raw text) | `"-9"`, `"-9.0"` | **Preserve 0**; confirmed sentinels $\to$ `NaN`; flag values $\notin \{0, 1\}$ |
| 7 | `restecg` | Discrete: 0 = Normal, 1 = ST-T abnorm., 2 = LVH | **Valid (0 = Normal ECG)** | `"?"` (raw text) | `"-9"`, `"-9.0"` | **Preserve 0**; confirmed sentinels $\to$ `NaN`; flag values $\notin \{0, 1, 2\}$ |
| 8 | `thalach` | Continuous beats/min max heart rate ($\sim 60–220$) | Invalid (heart rate $\le 0$ non-viable) | `"?"`, `0` | `"-9"`, `"-9.0"` | Values $\le 0$ or confirmed sentinels $\to$ `NaN`; flag values $< 50$ or $> 230$ |
| 9 | `exang` | Binary: 1 = Yes, 0 = No | **Valid (0 = No Angina)** | `"?"` (raw text) | `"-9"`, `"-9.0"` | **Preserve 0**; confirmed sentinels $\to$ `NaN`; flag values $\notin \{0, 1\}$ |
| 10 | `oldpeak` | Continuous mm ST depression ($\sim -2.6 \text{ to } 7.0$) | **Valid (0.0 = Isoelectric / Normal)** | `"?"` (raw text) | `"-9"`, `"-9.0"` | **Strictly preserve 0.0**; confirmed sentinels $\to$ `NaN`; preserve valid negative depression if documented |
| 14 | `target` (`num`) | Discrete: 0 = <50% stenosis, 1–4 = $\ge 50\%$ stenosis | **Valid (0 = Disease Free)** | None | None | Target conversion: $y = 0 \text{ if } num == 0 \text{ else } 1$; **never treat 0 as missing** |

#### C. The 5-Step Data Validation Contract
Data processing must strictly adhere to the following execution sequence:
1. **Parse Source Files**: Ingest each source file using its verified file format, token delimiter (whitespace vs comma), record structure (single-line vs multi-line per patient), and verified attribute mapping.
2. **Normalize Confirmed Sentinels**: Normalize only confirmed missing-value sentinels using feature-specific and cohort-specific rules (e.g. mapping `"?"` and physiologically impossible zeros for `chol`, `trestbps`, and `thalach` to IEEE NaN). Candidate sentinels (`"-9"`, `"-9.0"`) are normalized only if confirmed for that specific feature/cohort during implementation profiling.
3. **Validate Against Documented Domain**: Validate all parsed values against documented clinical domains and codebooks. Any out-of-domain value (e.g. unknown categories, unexpected strings, or unverified negative values) must be raised as an unexplained validation error, not silently remapped or converted to missing without empirical evidence.
4. **Preserve Legitimate Zero Values**: Explicitly assert that legitimate zero values (`sex=0`, `fbs=0`, `exang=0`, `restecg=0`, `oldpeak=0.0`, and `target=0`) remain intact, unaltered, and unflagged as missing.
5. **Training-Only Imputation & Scaling**: Within the Leave-One-Center-Out (LOCO) evaluation, fit all imputation (`SimpleImputer`), feature scaling (`StandardScaler`), missingness indicator generation, and probability calibration (`CalibratedClassifierCV`) strictly and exclusively using training centres. The held-out validation centre is transformed using the fitted training pipeline without updating any imputer statistics or calibration parameters.

#### D. Implementation Verification Requirements (Task 1.1 / 1.2 Inspection Protocol)
Because raw external `.data` files have not been downloaded during this documentation stage, the following conventions are explicitly designated for programmatic verification upon file download:
1. **Source File Record Layout**: Verify whether raw `hungarian.data` and `long-beach-va.data` use comma-delimited, whitespace-delimited, or fixed-width columns, and whether individual patient records span 10 lines of text (the 75-attribute format) or a single row (14-attribute processed format).
2. **Chest Pain Coding Verification**: Inspect raw values for attribute 3 (`cp`). The canonical codebook documents 1–4. If a local or preprocessed variant uses 0–3, verify the semantic correspondence (e.g. $0 \implies \text{typical angina}$) and apply the documented mapping $cp_{\text{canonical}} = cp + 1$. Do not silently remap unverified values.
3. **Sentinel Token Inventory (`-9` Check)**: Programmatically scan all attributes for `"-9"` or `"-9.0"`. Confirm whether `-9` functions as an intentional missing sentinel or an unexplained value on a per-feature, per-cohort basis before enabling replacement rules.
4. **Provisional Cholesterol Zero Counts**: Verify whether zero cholesterol counts match the provisional literature estimates (~23 in Hungary, ~131 in Long Beach VA), logging the exact empirical count and distribution.

### 4. Leave-One-Center-Out (LOCO) Cross-Validation Architecture

Evaluation uses a 3-fold LOCO procedure across the 736 patients:
- **Fold 1**: Train on Cleveland-Dev ($N=242$) + Long Beach VA ($N=200$) [$N_{\text{train}} = 442$] $\to$ Evaluate on Hungary ($N=294$, external).
- **Fold 2**: Train on Cleveland-Dev ($N=242$) + Hungary ($N=294$) [$N_{\text{train}} = 536$] $\to$ Evaluate on Long Beach VA ($N=200$, external).
- **Fold 3**: Train on Hungary ($N=294$) + Long Beach VA ($N=200$) [$N_{\text{train}} = 494$] $\to$ Evaluate on Cleveland-Dev ($N=242$, development baseline).

**Leakage Prevention Architecture**:
```
+---------------------------------------------------------------------------------+
|                                 LOCO Fold k                                     |
|                                                                                 |
|   +---------------------------------------+    +----------------------------+   |
|   |          Training Centres             |    |     Held-Out Center        |   |
|   |       (2 Centres, e.g. Cleve + VA)    |    |   (1 Centre, e.g. Hungary) |   |
|   +-------------------+-------------------+    +--------------+-------------+   |
|                       |                                       |                 |
|                       v                                       |                 |
|         [Steps 1-4: Validation Contract]                      |                 |
|                       |                                       |                 |
|                       v                                       v                 |
|         [Fit Imputers, Encoders & Scalers]     [Steps 1-4: Validation Contract] |
|                       |                                       |                 |
|                       v                                       |                 |
|           [Transform Training Data]                           |                 |
|                       |                                       |                 |
|                       v                                       |                 |
|      [Fit Estimator & Sigmoid Calibrator]                     |                 |
|                       |                                       |                 |
|                       +---------------------+                 |                 |
|                                             |                 |                 |
|                                             v                 v                 |
|                                     [Apply Fitted Pipeline to Held-Out]         |
|                                                       |                         |
|                                                       v                         |
|                                          [Generate Isolated Predictions]        |
|                                                       |                         |
|                                                       v                         |
|                                       [Compute Per-Center Metrics & CIs]        |
+---------------------------------------------------------------------------------+
```
- **Strict Data Integrity Rule**: All imputers, encoders, scalers, and probability calibrators are fitted solely on the training centres in that fold. The held-out centre acts strictly as an unseen, out-of-sample evaluation stream and must never influence preprocessing, imputer medians/modes, scaling statistics, calibration parameters, or model selection.
- **Model Family**: L2-regularised Logistic Regression (`C=1.0`), calibrated with `CalibratedClassifierCV(method='sigmoid', cv=5)` fitted on the training split, using a predefined decision threshold of $0.50$.

### 5. Statistical Rigor, Metrics & Uncertainty Reporting

- **Separate Reporting of Held-Out Results**:
  Results will be reported independently for each held-out centre:
  1. **Held-Out Hungary ($N=294$)**: External validation performance in a European referral setting.
  2. **Held-Out Long Beach VA ($N=200$)**: External validation performance in an older, high-missingness US veteran setting.
  3. **Held-Out Cleveland Development ($N=242$)**: Retrospective development baseline performance (disclosed as familiar development data, not independent confirmation).
- **Per-Center Metric Suite**:
  - Discrimination: ROC-AUC, Average Precision (PR-AUC).
  - Classification (Threshold 0.50): Accuracy, Sensitivity (Recall), Specificity, Precision, F1-Score.
  - Calibration: Calibrated Brier Score, Expected Calibration Error (ECE, 10 equal-frequency bins).
- **Uncertainty Bounds & Limitations**:
  - **Within-Cohort Uncertainty**: 95% bootstrap confidence intervals derived via 1,000 stratified resamples per held-out centre quantify statistical sampling variation *within each observed cohort*, conditional on that cohort's specific sampling frame and case mix. They do *not* quantify uncertainty across future unobserved hospitals or health systems.
  - **Multi-Centre Generalisation Limitation**: Acknowledged explicitly that three historical centres ($N=3$) provide limited empirical evidence about generalisation across broader healthcare institutions, different clinical practice patterns, or modern patient demographics.
- **Summary Metrics**:
  - Macro-average: Unweighted arithmetic mean across the three centres (treating each clinical institution as an equal domain).
  - Micro-average: Pooled aggregate across all $N=736$ predictions.

### 6. Isolation of Cleveland Locked Test Set ($N=61$)

- The 61-sample locked Cleveland test set in `data/processed/` (tracked via `data/raw/train_test_split.json`) is strictly quarantined.
- Neither the LOCO training nor the LOCO evaluation will load, merge, pre-process, or inspect the 61 locked test patients.
- The Cleveland centre in LOCO is represented exclusively by the 242 development samples.

### 7. Provenance, Licensing & Clinical Scope

- **Attribution**: UCI Machine Learning Repository Heart Disease Dataset:
  *Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1988). Heart Disease. UCI Machine Learning Repository. DOI: 10.24432/C56327.*
- **Licensing Compliance**: Full compliance with the Creative Commons Attribution 4.0 International (CC BY 4.0) license.
- **Regulatory & Clinical Disclaimer**: Open-source license compliance governs copyright and intellectual property distribution only; it does **not** constitute, imply, or substitute for clinical validation, ethical clearance, medical device certification, or regulatory approval (e.g. FDA 510(k), CE mark, SaMD) for clinical use.

## Risks / Trade-offs

- **Risk: Institutional Referral Bias (Verification Bias)** -> *Mitigation*: Historical cohorts reflect patients referred for invasive coronary angiography rather than asymptomatic screening populations. The design explicitly documents that findings reflect diagnostic catheterization transportability, not broad population screening accuracy.
- **Risk: Naive Global Zero Replacement** -> *Mitigation*: The feature-specific sentinel matrix explicitly forbids global zero-to-NaN conversions, protecting valid zero measurements for `sex=0`, `fbs=0`, `exang=0`, `restecg=0`, `oldpeak=0.0`, and `target=0`.
- **Risk: Unverified Sentinel Assumptions (`-9`)** -> *Mitigation*: Sentinels outside `"?"` are treated as unverified candidate hypotheses requiring automated confirmation during implementation profiling, preventing unintended data corruption.
- **Risk: Extreme Missingness in Long Beach Cholesterol (65.5% provisional)** -> *Mitigation*: The dual-architecture design explicitly compares the 11-input missing-aware model against the 9-input model (9 clinical features, omitting `chol`), identifying whether cholesterol can be safely eliminated without sacrificing discrimination.
- **Risk: Conflating Cleveland Held-Out Score with External Generalisation** -> *Mitigation*: The reporting framework explicitly partitions results into external centres (Hungary, Long Beach) versus retrospective development baseline (Cleveland), preventing misinterpretation of Cleveland performance as fresh independent confirmation.
- **Risk: Overinterpreting Patient-Level Bootstrap Intervals** -> *Mitigation*: Documentation explicitly clarifies that bootstrap intervals reflect within-cohort sampling variability, and that three historical centres provide limited evidence regarding generalisation across healthcare institutions.
- **Risk: Leakage via Center-Pooled Preprocessing** -> *Mitigation*: Pipeline encapsulation ensures that fit calls occur strictly on the training partition of each fold. Dedicated regression tests (`tests/test_multicenter_leakage.py`) will assert that imputer statistics are identical to training partition statistics and have zero mathematical dependence on held-out centre test data.

## Open Questions

- None. All major design choices (cohort selection, Switzerland exclusion, feature harmonisation, consistent feature counts, feature-specific sentinel conventions, cholesterol comparison strategy, LOCO validation protocol, uncertainty interpretation, and test-set quarantine) are resolved, with unverified raw layout details assigned to implementation verification tasks.
