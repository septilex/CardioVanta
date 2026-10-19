# Phase 16: Feature Engineering & Robust Representation Research Report

**Document ID:** `reports/phase16_feature_engineering.md`  
**Execution Date:** 2026-10-12  
**Git HEAD:** `e79026affd88f2f7dc3ab52387b5c4aae87f7f10`  
**Environment:** Python 3.11.9, scikit-learn 1.9.1, NumPy 2.4.6, pandas 3.0.6  
**OpenSpec Change:** `openspec/changes/phase-16-feature-engineering/`  
**Authoritative Dataset:** `data/raw/heart.csv` (SHA256: `7c3014365675306819510a49ff289efbec1d1a6a666a2dc7652f1547b383d859`)  

---

## 1. Executive Summary

This study implemented and executed the approved CardioVanta Phase 16 research protocol under strict, duplicate-aware 5×5 Global Nested Cross-Validation with fold-local sigmoid calibration. The objective was to test whether carefully motivated clinical feature representations—specifically an **interaction term ($z_{\text{age}} \times z_{\text{thalach}}$)**, a **quadratic term ($(z_{\text{oldpeak}})^2$)**, or their **combination**—yield a demonstrable improvement over the frozen Logistic Regression baseline.

### Key Findings
1. **Selection Procedure Performance:**
   - **Baseline OOF Accuracy:** **85.54%** (207/242), Recall: 88.64%, ROC-AUC: 0.9163, Brier Score: 0.1164.
   - **Selection Procedure OOF Accuracy:** **85.95%** (208/242), Recall: 89.39%, ROC-AUC: 0.9142, Brier Score: 0.1167.
   - **Observed Accuracy Gain:** **+0.41 percentage points (+0.0041 absolute)**, which falls significantly short of the predefined adoption threshold of **+1.5 percentage points (+0.0150 absolute)**.
2. **Predefined Adoption Gate:** **REJECTED**. The procedure satisfied the recall condition ($89.39\% > 85\%$) but failed the minimum accuracy improvement gate ($+0.41\text{ pp} < +1.50\text{ pp}$).
3. **Full Development Data Model Selection:** When evaluated across all 5 inner folds of the full development set ($N=242$), **Candidate A (Baseline)** achieved the highest inner-CV ROC-AUC ($0.9163$), outperforming Candidate C ($0.9161$), Candidate B ($0.9139$), and Candidate D ($0.9136$). Baseline was selected as the final representation.
4. **Retrospective Locked-Test Evaluation ($N=61$):** Because Candidate A was selected on full development data, the locked-test evaluation is identical to the baseline:
   - **Accuracy:** **86.89%** (53/61)
   - **Recall:** **93.94%** (31/33)
   - **ROC-AUC:** **0.9048**
   - **Confusion Matrix:** TN=22, FP=6, FN=2, TP=31
   *(Note: This evaluation is strictly retrospective and exploratory because the locked test set was previously inspected during historical error analysis).*
5. **Production Recommendation:** **MAINTAIN FROZEN BASELINE**. Production model artifacts, schemas, and thresholds remain completely untouched.

---

## 2. Research Design & Candidate Representations

The experiment strictly bounded candidate representations to exactly four candidates within standard scikit-learn `Pipeline` architectures. Preprocessing and scaling parameters were fitted strictly on fold training data.

### Baseline Preprocessor
The foundation is the linear preprocessor (`PreprocessingFactory('linear')`), producing a 27-dimensional feature vector:
- **Continuous Features (StandardScaler):** Column 0: `age`, Column 3: `thalach`, Column 4: `oldpeak` (along with `trestbps` and `chol`).
- **Binary Features (Passthrough):** `sex`, `fbs`, `exang`.
- **Categorical Features (OneHotEncoder):** `cp`, `restecg`, `slope`, `ca`, `thal`.

### Mathematical Definitions of Candidates

| Candidate | Name | Mathematical Transformation | Dimensions | Simplicity Rank |
| :--- | :--- | :--- | :---: | :---: |
| **A** | **Frozen Baseline** | Identity passthrough of 27 baseline features | 27 | **1** |
| **B** | **Age × Thalach Interaction** | $u_{\text{inter}} = z_{\text{age}} \cdot z_{\text{thalach}}$, standardized as $\frac{u_{\text{inter}} - \mu_{\text{inter}}}{\sigma_{\text{inter}}}$ | 28 | **2** |
| **C** | **Oldpeak Squared** | $u_{\text{sq}} = (z_{\text{oldpeak}})^2$, standardized as $\frac{u_{\text{sq}} - \mu_{\text{sq}}}{\sigma_{\text{sq}}}$ | 28 | **3** |
| **D** | **Combined** | Both standardized interaction and squared terms appended | 29 | **4** |

Where $z_{\text{age}}, z_{\text{thalach}}, z_{\text{oldpeak}}$ are the standardized feature outputs from the training fold, and $\mu, \sigma$ are the mean and standard deviation of the transformed terms calculated strictly on the training partition of the respective fold.

### Estimator Hyperparameters
All candidates use the identical frozen estimator:
```python
LogisticRegression(
    C=0.1,
    penalty="l2",
    class_weight="balanced",
    solver="lbfgs",
    max_iter=1000,
    random_state=42
)
```

---

## 3. Candidate Selection & Nested CV Methodology

### Frozen Selection Rule
Inner-CV ranking evaluated the raw, uncalibrated out-of-fold ROC-AUC across identical 5 inner folds within the outer-training partition:
1. Candidate with the maximum mean inner ROC-AUC is identified ($\text{AUC}_{\max}$).
2. Candidates within tie tolerance are considered tied:
   $$\text{AUC}_{\max} - \text{AUC}_{\text{cand}} \le 0.0001$$
3. Among tied candidates, the candidate with the lowest simplicity rank (Rank 1: A $\to$ Rank 2: B $\to$ Rank 3: C $\to$ Rank 4: D) is selected.

### Duplicate-Aware Grouping
Exact duplicate feature rows in the raw dataset ($N=242$ development samples, 241 unique duplicate groups) were partitioned using `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`. Duplicate group boundaries were strictly preserved across:
- Outer cross-validation splits.
- Inner candidate-selection splits.
- Calibration fitting splits.

### Fold-Local Probability Calibration
To prevent validation leakage:
- Calibration models (`CalibratedClassifierCV(estimator=pipeline, method='sigmoid', cv=cv_calib)`) were fitted **exclusively on outer-training data**.
- An explicit, precomputed generator of `StratifiedGroupKFold(5)` on outer-training groups was supplied to `cv_calib`. Integer defaults (`cv=5`) were avoided to prevent group leakage.
- Outer-validation samples were strictly evaluated out-of-fold using the calibrated pipeline.
- Threshold was fixed at $P(y=1) \ge 0.5$ (no threshold search on validation or test sets).

---

## 4. Empirical Evaluation Results

### 4.1 Outer-Fold Breakdown

| Outer Fold | Train $N$ | Val $N$ | Candidate Selected | Inner ROC-AUC (Selected) | Val Baseline Acc | Val Selected Acc | Val Baseline Recall | Val Selected Recall |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 193 | 49 | **Candidate A** | 0.9269 | 83.67% | 83.67% | 88.89% | 88.89% |
| **2** | 194 | 48 | **Candidate A** | 0.9201 | 83.33% | 83.33% | 92.31% | 92.31% |
| **3** | 194 | 48 | **Candidate A** | 0.9125 | 89.58% | 89.58% | 96.15% | 96.15% |
| **4** | 193 | 49 | **Candidate A** | 0.9147 | 85.71% | 85.71% | 81.48% | 81.48% |
| **5** | 194 | 48 | **Candidate D** | 0.9168 | 85.42% | 87.50% | 84.62% | 88.46% |

In outer folds 1 through 4, Candidate A dominated the inner-CV ranking. In outer fold 5, Candidate D attained a higher inner ROC-AUC (0.9168 vs 0.9114 for A) and yielded a minor accuracy increase in outer fold 5 (+2.08 pp, 1 additional correct sample).

#### 4.1.1 Fold Metric Dispersion & Standard Deviation Reconciliation

The experiment recorded fold-by-fold validation performance across both arms. Below is the complete recomputed distribution of fold metrics, including both **population standard deviation** ($\text{ddof}=0$) and **sample standard deviation** ($\text{ddof}=1$, Bessel's correction):

| Metric | Baseline Fold Mean | Baseline Pop Std ($\text{ddof}=0$) | Baseline Sample Std ($\text{ddof}=1$) | Selected Fold Mean | Selected Pop Std ($\text{ddof}=0$) | Selected Sample Std ($\text{ddof}=1$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Accuracy** | 85.5442% (0.855442) | 2.2247% (0.022247) | 2.4873% (0.024873) | 85.9609% (0.859609) | 2.3532% (0.023532) | 2.6310% (0.026310) |
| **Recall** | 88.6895% (0.886895) | 5.2422% (0.052422) | 5.8609% (0.058609) | 89.4587% (0.894587) | 4.8559% (0.048559) | 5.4290% (0.054290) |
| **Specificity** | 81.8182% (0.818182) | 6.4282% (0.064282) | 7.1870% (0.071870) | 81.8182% (0.818182) | 6.4282% (0.064282) | 7.1870% (0.071870) |
| **Precision** | 85.7264% (0.857264) | 4.0568% (0.040568) | 4.5356% (0.045356) | 85.8187% (0.858187) | 4.1123% (0.041123) | 4.5977% (0.045977) |
| **F1 Score** | 0.869773 | 0.019818 | 0.022157 | 0.874147 | 0.020194 | 0.022577 |
| **ROC-AUC** | 0.920396 | 0.017370 | 0.019420 | 0.917949 | 0.015623 | 0.017467 |
| **Average Precision** | 0.926937 | 0.027654 | 0.030918 | 0.925068 | 0.026319 | 0.029425 |
| **Brier Score** | 0.116332 | 0.012600 | 0.014087 | 0.116576 | 0.012413 | 0.013878 |
| **Log Loss** | 0.372966 | 0.029383 | 0.032852 | 0.376104 | 0.026068 | 0.029145 |

**Mathematical & Aggregation Reconciliation Notes:**
1. **Standard Deviation Definition:** The JSON artifact `experiments/results/phase16_feature_engineering.json` reports `acc_std` and `recall_std` in `nested_cv.fold_summary` using NumPy's default `ddof=0` (population standard deviation: $\sigma = \sqrt{\frac{1}{K}\sum_{k=1}^K (x_k - \bar{x})^2}$). When calculated as an unbiased sample standard deviation with Bessel's correction ($\text{ddof}=1$: $s = \sqrt{\frac{1}{K-1}\sum_{k=1}^K (x_k - \bar{x})^2}$ with $K=5$), the values scale by $\sqrt{K/(K-1)} = \sqrt{5/4} \approx 1.118034$, yielding $s_{\text{acc}} = 2.49\%$ for baseline and $s_{\text{acc}} = 2.63\%$ for the selected procedure. Both formulations are fully documented above to eliminate numerical ambiguity.
2. **Fold Mean vs. Pooled Aggregate:** Because the outer folds have slightly unequal validation partition sizes (Folds 1 & 4 have $N=49$; Folds 2, 3, & 5 have $N=48$), the unweighted arithmetic mean of fold metrics (e.g., Selected Mean Acc: 85.9609%, Baseline Mean Acc: 85.5442%) differs slightly in fractional decimals from the pooled out-of-fold aggregate metrics evaluated across all 242 development samples (Selected Pooled Acc: 208/242 = 85.9504%, Baseline Pooled Acc: 207/242 = 85.5372%). Both representations round to 85.95% and 85.54%, respectively.

### 4.2 Aggregate Out-of-Fold (OOF) Metrics ($N=242$)

The primary evaluation criterion evaluates the pooled predictions of the complete procedure across all 242 development samples:

| Metric | Calibrated Baseline | Calibrated Selection Procedure | Delta (Selected - Baseline) |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **85.5372% (207/242)** | **85.9504% (208/242)** | **+0.4132 pp (+0.004132)** |
| **Recall (Sensitivity)** | **88.6364% (117/132)** | **89.3939% (118/132)** | **+0.7576 pp (+0.007576)** |
| **Specificity** | **81.8182% (90/110)** | **81.8182% (90/110)** | **0.0000 pp (+0.000000)** |
| **Precision** | **85.4015% (117/137)** | **85.5072% (118/138)** | **+0.1058 pp (+0.001058)** |
| **F1 Score** | 0.869888 | 0.874074 | +0.004186 |
| **ROC-AUC** | 0.916253 | 0.914187 | -0.002066 |
| **Average Precision** | 0.919734 | 0.918847 | -0.000888 |
| **Brier Score** | 0.116428 | 0.116670 | +0.000242 (worse) |
| **Log Loss** | 0.373220 | 0.376333 | +0.003113 (worse) |
| **True Positives (TP)** | 117 | 118 | +1 |
| **False Negatives (FN)** | 15 | 14 | -1 |
| **True Negatives (TN)** | 90 | 90 | 0 |
| **False Positives (FP)** | 20 | 20 | 0 |

Across the entire 242-observation development set, the experimental selection procedure flipped exactly 1 observation from False Negative to True Positive (in Fold 5), leaving the remaining 241 predictions completely unchanged.

---

## 5. Predefined Adoption Gate Analysis

The experimental protocol established two mandatory gates that must both be satisfied for representation adoption:
1. **Gate 1 (Accuracy Improvement):** $\Delta \text{Acc} \ge +0.0150$ (+1.5 percentage points absolute).
   - *Result:* $\Delta \text{Acc} = +0.004132$ (+0.41 percentage points).
   - *Status:* **FAILED** (fell short by 1.09 percentage points).
2. **Gate 2 (Recall Maintenance):** $\text{Recall}_{\text{selected}} > 0.8500$.
   - *Result:* $\text{Recall}_{\text{selected}} = 0.893939$ (89.39%).
   - *Status:* **PASSED**.

**Decision:** **REJECT ADOPTION**. Because Gate 1 was not satisfied, the experimental representation procedure fails the adoption criteria. Production baseline remains in place.

---

## 6. Full Development Model Selection & Retrospective Locked-Test Evaluation

### Selection on Complete Development Set ($N=242$)
Applying the selection rule across 5-fold inner CV on the full development set produced:
- **Candidate A (Baseline):** ROC-AUC = **0.916253**
- **Candidate C (Oldpeak Squared):** ROC-AUC = **0.916116**
- **Candidate B (Age × Thalach):** ROC-AUC = **0.913912**
- **Candidate D (Combined):** ROC-AUC = **0.913567**

Because Candidate A achieved the highest inner ROC-AUC (and even with the 0.0001 tie tolerance, Candidate C was 0.000137 below A, while Candidate A also possesses Simplicity Rank 1), **Candidate A (Baseline)** was selected as the final model representation.

### Retrospective Locked-Test Assessment ($N=61$)
Evaluating the final fitted and calibrated model against the locked test partition yielded:
- **Accuracy:** **86.8852%** (53 / 61 correct)
- **Recall:** **93.9394%** (31 / 33)
- **Specificity:** **78.5714%** (22 / 28)
- **Precision:** **83.7838%** (31 / 37)
- **F1 Score:** **0.885714**
- **ROC-AUC:** **0.904762**
- **Brier Score:** **0.128014**
- **Log Loss:** **0.399679**
- **Confusion Matrix:** TN=22, FP=6, FN=2, TP=31

**Scientific Context:** This locked-test evaluation is identical to the baseline performance because Candidate A was selected. As mandated by protocol, this locked-test evaluation is documented strictly as a retrospective assessment and is not interpreted as confirmatory evidence of generalization.

---

## 7. Artifact Integrity & Provenance Verification

All production model files, hashes, and configurations were audited before and after execution:

| Artifact Path | SHA256 Hash | Status |
| :--- | :--- | :---: |
| `artifacts/model/model.joblib` | `18e2268e797020e6a24da44ae7279e39581f7bab5bffb3c8d31dcf2ea379a348` | **UNCHANGED** |
| `artifacts/model/explanation_model.joblib` | `da66de612a2bb2d45ecf1319bb2e07708c76688da2b54c2e529c6f6d7186aecc` | **UNCHANGED** |
| `artifacts/model/metadata.json` | `c6936399f27a8f20c04106cb6f5e4dcbc88a4cb71593b69ff0d04dd739bb883d` | **UNCHANGED** |
| `data/raw/heart.csv` | `7c3014365675306819510a49ff289efbec1d1a6a666a2dc7652f1547b383d859` | **UNCHANGED** |

---

## 8. Conclusion and Future Research

1. **Hypothesis Evaluation (Bounded Scope):** Under duplicate-aware 5×5 nested cross-validation with fold-local sigmoid calibration, the four evaluated representations—Baseline (Candidate A), Age × Thalach interaction (Candidate B), Oldpeak squared quadratic (Candidate C), and their Combination (Candidate D)—achieved an aggregate out-of-fold accuracy gain of only +0.41 percentage points (208/242 vs 207/242), altering predictions on only 1 observation out of 242.
2. **Adoption Gate Decision:** These four specific candidate representations failed the predefined engineering adoption threshold ($\Delta \text{Acc} \ge +1.50\text{ pp}$), resulting in an unambiguous **REJECT** decision. The production baseline remains fully in place.
3. **Appropriately Bounded Claims:** This experiment specifically established that the two hypothesized feature transformations ($z_{\text{age}} \times z_{\text{thalach}}$ and $(z_{\text{oldpeak}})^2$) do not satisfy the adoption gate when paired with the frozen logistic regression architecture under duplicate-aware calibration. This empirical finding does **not** imply that all conceivable feature representations or non-linear terms have been exhausted, nor does it establish that feature engineering as a broader methodology is invalid for cardiovascular risk prediction.
4. **Accuracy Ceilings & 95% Benchmark:** The target of 95% accuracy remains unmet by the four evaluated representations on this 303-patient dataset ($N=242$ development, $N=61$ locked test). Crucially, this study does **not** prove that an insurmountable theoretical accuracy ceiling exists on this dataset or clinical domain. Whether alternative representation paradigms, non-linear modeling families, or substantially larger cohorts could attain higher performance remains an open empirical question.
5. **Production Baseline Stability:** Because the adoption gate failed and Candidate A was chosen on the full development set, production model artifacts, calibration parameters, classification threshold (0.5), inference services, and schemas remain completely unmodified.
