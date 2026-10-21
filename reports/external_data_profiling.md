# CardioVanta Phase 17: External Dataset Profiling & Provenance Report

## 1. Executive Summary & Provenance Verification

- **Dataset**: UCI Heart Disease (UCI Machine Learning Repository ID: 45)
- **DOI**: [10.24432/C56327](https://doi.org/10.24432/C56327)
- **License**: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) (`CC-BY-4.0`)
- **Curator**: David W. Aha, July 1988

> [!IMPORTANT]
> **Regulatory & Clinical Disclaimer**: Open-source licensing compliance governs copyright and distribution only. It does NOT constitute, imply, or substitute for clinical validation, ethical clearance, medical device certification, or regulatory approval (such as FDA 510(k), CE mark, or SaMD classification) for clinical, diagnostic, or therapeutic patient care.

### Formal Citation Attribution
1. **Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1988).** *Heart Disease.* UCI Machine Learning Repository. https://doi.org/10.24432/C56327
2. **Detrano, R., Janosi, A., Steinbrunn, W., Pfisterer, M., Schmid, J., Sandhu, S., Guppy, K., Lee, S., & Froelicher, V. (1989).** *International application of a new probability algorithm for the diagnosis of coronary artery disease.* American Journal of Cardiology, 64(5), 304–310.

## 2. Cryptographic Integrity & File Manifest

| Cohort / File | Source File | Expected Records | Size (Bytes) | SHA-256 Checksum | Integrity Status |
|---|---|---|---|---|---|
| Hungarian Cohort (Budapest) | `hungarian.data` | 294 | 62192 | `b8e4bbd06b9bf9ec831c992ba397639f22815e525c43b489e1a6e75b3be29a75` | VERIFIED [MATCH] |
| Long Beach VA Cohort (California) | `long-beach-va.data` | 200 | 39892 | `16d44b28ccb139d07509ee17f22c51fcd568caea8beb607d1503e4a679133353` | VERIFIED [MATCH] |

## 3. Empirical Data Findings & Contract Verification

### A. Raw Record Layout & Delimiters
- Raw source files (`hungarian.data`, `long-beach-va.data`) utilize whitespace-delimited tokens spanning **exactly 10 physical lines per patient**.
- Each patient record terminates strictly with the token `'name'` (attribute 76), yielding **exactly 76 tokens per record** without parsing ambiguities.
- Parsing counts match verified clinical cohort targets: **Hungary $N=294$**, **Long Beach VA $N=200$**.

### B. Chest Pain (`cp`) Category Coding Verification
- The canonical UCI codebook defines `cp` as: `1` = typical angina, `2` = atypical angina, `3` = non-anginal pain, `4` = asymptomatic.
- **Empirical Result**: BOTH cohorts exhibit canonical **1–4 coding**.
  - Zero occurrences of `0` were detected in either raw dataset.
  - Applying `cp + 1` remapping would corrupt valid data; canonical 1–4 coding is empirically validated.

| Cohort | cp=1 (Typical) | cp=2 (Atypical) | cp=3 (Non-anginal) | cp=4 (Asymptomatic) | Zero Count | Canonical 1–4 Verified |
|---|---|---|---|---|---|---|
| Hungarian Cohort (Budapest) | 11 (3.7%) | 106 (36.1%) | 54 (18.4%) | 123 (41.8%) | 0 | YES |
| Long Beach VA Cohort (California) | 8 (4.0%) | 14 (7.0%) | 47 (23.5%) | 131 (65.5%) | 0 | YES |

### C. Sentinel Token Inventory (`?` vs `-9`)
- Primary UCI documentation notes `-9.0` as missing sentinel in raw files.
- **Empirical Result**: In raw 76-attribute files, candidate missing sentinel is exclusively `'-9'`.
  - `?` occurs 0 times in raw files (it was introduced downstream in David Aha's comma-separated extracts).
  - Feature-specific sentinel distribution in raw files:

| Feature | Hungary (`-9` count) | Long Beach VA (`-9` count) | Valid 0 Interpretation |
|---|---|---|---|
| `age` | 0 | 0 | UNPHYSIOLOGICAL |
| `sex` | 0 | 0 | PROTECTED ZERO |
| `cp` | 0 | 0 | UNPHYSIOLOGICAL |
| `trestbps` | 1 | 56 | UNPHYSIOLOGICAL |
| `chol` | 23 | 7 | UNPHYSIOLOGICAL |
| `fbs` | 8 | 7 | PROTECTED ZERO |
| `restecg` | 1 | 0 | PROTECTED ZERO |
| `thalach` | 1 | 53 | UNPHYSIOLOGICAL |
| `exang` | 1 | 53 | PROTECTED ZERO |
| `oldpeak` | 0 | 56 | PROTECTED ZERO |
| `slope` | 190 | 101 | UNPHYSIOLOGICAL |
| `ca` | 290 | 198 | UNPHYSIOLOGICAL |
| `thal` | 266 | 159 | UNPHYSIOLOGICAL |
| `num` | 0 | 0 | PROTECTED ZERO |

### D. Cholesterol Value Accounting (`chol == 0` vs Literature Estimates)

| Cohort | Literature Estimate | Empirical `chol == 0` | Empirical `chol == -9` | Valid Positive Count | Median Positive | Reconciliation Findings |
|---|---|---|---|---|---|---|
| Hungarian Cohort (Budapest) | ~23 | 0 | 23 | 271 | 243.0 mg/dl | Confirmed 23 missing sentinels (-9) in Hungary; raw chol=0 count is 0. |
| Long Beach VA Cohort (California) | ~131 | 49 | 7 | 144 | 228.0 mg/dl | Confirmed 49 exact zeros (chol=0) and 7 sentinels (-9) in Long Beach VA. |

### E. Preservation of Legitimate Zero Values
The following legitimate zero clinical measurements and binary classes are confirmed intact and MUST NOT be converted to NaN:

| Legitimate Zero Field | Clinical Semantic | Hungary (Zero Count) | Long Beach VA (Zero Count) |
|---|---|---|---|
| `sex = 0` | Female Biological Sex | 81 | 6 |
| `fbs = 0` | Fasting Blood Sugar <= 120 mg/dl | 266 | 125 |
| `restecg = 0` | Normal Resting Electrocardiogram | 235 | 80 |
| `exang = 0` | No Exercise-Induced Angina | 204 | 52 |
| `oldpeak = 0.0` | Isoelectric Normal ST Depression | 189 | 40 |
| `num = 0` | Disease-Free Negative Control Label | 188 | 51 |

### F. Domain Anomalies and Physiological Edge Cases
#### Hungarian Cohort (Budapest)
- No domain anomalies detected.
#### Long Beach VA Cohort (California)
- Physiologically unviable blood pressure: record #33 trestbps=0 mm Hg.
- Documented negative ST depression: record #5 oldpeak=-0.5 mm (valid ST elevation/depression).
- Out-of-domain slope value: record #100 slope=0 (canonical domain is 1, 2, 3).

## 4. Documentation of Resolved and Unresolved Questions

1. **Resolved: CP Coding**: Confirmed canonical 1–4 coding across all 494 external patient records.
2. **Resolved: Raw Delimiters**: Confirmed 10 lines per patient ending in token `'name'` (76 attributes).
3. **Resolved: Raw Sentinels**: Confirmed `'-9'` represents missingness in raw files; `'?'` was added in secondary comma-delimited extracts.
4. **Resolved: Cholesterol Count Discrepancy**: Hungary has 23 instances of `'-9'` (0 instances of `'0'`). Long Beach VA has 49 instances of `'0'` and 7 instances of `'-9'` (total 56 non-positive/missing), while 144 patients have valid positive cholesterol.
5. **Unresolved Question**: In Long Beach VA, record #33 contains `trestbps = 0`, which is physiologically non-viable. In Step 3 validation, this will be normalized to NaN alongside unviable `chol = 0`.