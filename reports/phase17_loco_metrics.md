# Phase 17: Per-Centre Multicenter Validation Metrics & Bootstrap Uncertainty Report

**Document ID:** `reports/phase17_loco_metrics.md`  
**Generated:** 2026-10-21T05:40:57.392226+00:00  
**Evaluation Scheme:** 3-Fold Leave-One-Centre-Out (LOCO) Cross-Validation  
**Decision Threshold:** Fixed 0.50 (untuned)  
**Uncertainty Estimation:** Stratified Percentile Bootstrap (1,000 replicates, 95% two-sided CI)  
**Authoritative Source:** UCI Machine Learning Repository (CC BY 4.0)  

---

## 1. Executive Summary

This report provides rigorous per-centre performance quantification and uncertainty bounds for:
- **Candidate A**: Missing-Aware 10-Clinical-Feature Pipeline (11 Model Inputs, including `chol_is_missing`).
- **Candidate B**: Non-Invasive 9-Clinical-Feature Pipeline (9 Model Inputs, systematically omitting `chol`).

Both architectures use L2-regularized Logistic Regression ($C=1.0$) with training-only Platt sigmoid probability calibration (`CalibratedClassifierCV`, 5-fold stratified internal CV).

### Clinical Context & Target Semantics

- **Target Definition**: Disease present is strictly designated as the positive class ($y=1$, angiographic diameter narrowing $> 50\%$); disease-free ($< 50\%$ narrowing) is designated as the negative class ($y=0$), harmonized consistently across all three clinical cohorts.
- **Cohort Roles**: Hungary ($N=294$) and Long Beach VA ($N=200$) serve as independent external-validation cohorts. Cleveland Development ($N=242$) is evaluated as a retrospective development-centre comparison.
- **Quarantined Partition**: The separate 61-sample locked Cleveland test partition is strictly excluded from all training, calibration, and prediction evaluations.

### Key Multi-Centre Findings

### Hungary (External Validation Centre (Europe))
**Cohort Size:** $N=294$ patients (Positives: 106, Negatives: 188, Prevalence: 36.1%)

| Metric | Candidate A (11 Inputs) [95% CI] | Candidate B (9 Inputs) [95% CI] | Difference (A - B) |
|:---|:---:|:---:|:---:|
| ROC-AUC | 0.8858 [0.8426, 0.9276] | 0.8897 [0.8466, 0.9306] | -0.0039 |
| PR-AUC (Average Precision) | 0.8481 [0.7902, 0.9073] | 0.8503 [0.7944, 0.9086] | -0.0023 |
| Accuracy (t=0.50) | 0.8197 [0.7755, 0.8639] | 0.8265 [0.7823, 0.8673] | -0.0068 |
| Sensitivity / Recall (t=0.50) | 0.7642 [0.6792, 0.8396] | 0.7547 [0.6698, 0.8302] | +0.0094 |
| Specificity (t=0.50) | 0.8511 [0.7977, 0.8989] | 0.8670 [0.8138, 0.9149] | -0.0160 |
| Precision / PPV (t=0.50) | 0.7431 [0.6777, 0.8142] | 0.7619 [0.6930, 0.8333] | -0.0188 |
| F1-Score (t=0.50) | 0.7535 [0.6919, 0.8131] | 0.7583 [0.6931, 0.8186] | -0.0048 |
| Brier Score | 0.1312 [0.1099, 0.1516] | 0.1270 [0.1060, 0.1478] | +0.0042 |
| Expected Calibration Error (ECE, 10-bin) | 0.0936 [0.0754, 0.1327] | 0.0767 [0.0623, 0.1170] | +0.0169 |

### Long Beach (External Validation Centre (US Veteran))
**Cohort Size:** $N=200$ patients (Positives: 149, Negatives: 51, Prevalence: 74.5%)

| Metric | Candidate A (11 Inputs) [95% CI] | Candidate B (9 Inputs) [95% CI] | Difference (A - B) |
|:---|:---:|:---:|:---:|
| ROC-AUC | 0.7523 [0.6610, 0.8264] | 0.7596 [0.6726, 0.8316] | -0.0073 |
| PR-AUC (Average Precision) | 0.8800 [0.8241, 0.9252] | 0.8871 [0.8378, 0.9287] | -0.0071 |
| Accuracy (t=0.50) | 0.6700 [0.6000, 0.7301] | 0.7050 [0.6400, 0.7700] | -0.0350 |
| Sensitivity / Recall (t=0.50) | 0.6376 [0.5570, 0.7114] | 0.7047 [0.6309, 0.7785] | -0.0671 |
| Specificity (t=0.50) | 0.7647 [0.6471, 0.8824] | 0.7059 [0.5686, 0.8240] | +0.0588 |
| Precision / PPV (t=0.50) | 0.8879 [0.8347, 0.9369] | 0.8750 [0.8231, 0.9231] | +0.0129 |
| F1-Score (t=0.50) | 0.7422 [0.6800, 0.7955] | 0.7807 [0.7245, 0.8316] | -0.0385 |
| Brier Score | 0.2158 [0.1850, 0.2488] | 0.1902 [0.1612, 0.2210] | +0.0256 |
| Expected Calibration Error (ECE, 10-bin) | 0.2086 [0.1776, 0.2626] | 0.1566 [0.1273, 0.2086] | +0.0520 |

### Cleveland (Retrospective Development Baseline (Familiar Case Mix))
**Cohort Size:** $N=242$ patients (Positives: 110, Negatives: 132, Prevalence: 45.5%)

| Metric | Candidate A (11 Inputs) [95% CI] | Candidate B (9 Inputs) [95% CI] | Difference (A - B) |
|:---|:---:|:---:|:---:|
| ROC-AUC | 0.8703 [0.8257, 0.9123] | 0.8691 [0.8250, 0.9110] | +0.0012 |
| PR-AUC (Average Precision) | 0.8615 [0.8117, 0.9080] | 0.8602 [0.8109, 0.9083] | +0.0012 |
| Accuracy (t=0.50) | 0.7686 [0.7149, 0.8182] | 0.7645 [0.7149, 0.8140] | +0.0041 |
| Sensitivity / Recall (t=0.50) | 0.8000 [0.7273, 0.8727] | 0.7818 [0.7091, 0.8545] | +0.0182 |
| Specificity (t=0.50) | 0.7424 [0.6667, 0.8106] | 0.7500 [0.6742, 0.8182] | -0.0076 |
| Precision / PPV (t=0.50) | 0.7213 [0.6641, 0.7838] | 0.7227 [0.6667, 0.7885] | -0.0014 |
| F1-Score (t=0.50) | 0.7586 [0.7043, 0.8070] | 0.7511 [0.6975, 0.8036] | +0.0075 |
| Brier Score | 0.1484 [0.1256, 0.1724] | 0.1482 [0.1249, 0.1724] | +0.0002 |
| Expected Calibration Error (ECE, 10-bin) | 0.0636 [0.0532, 0.1159] | 0.0632 [0.0515, 0.1202] | +0.0004 |

---

## 2. Statistical Methodology & Rigor

1. **Discrimination**:
   - **ROC-AUC**: Evaluates global ranking ability across all operating thresholds.
   - **PR-AUC (Average Precision)**: Evaluates precision-recall trade-off under cohort-specific prevalence. Computed explicitly as Average Precision rather than trapezoidal Riemann sum.
2. **Threshold Classification (Fixed $t=0.50$)**:
   - Evaluated without empirical threshold tuning or post-hoc threshold selection.
   - Diagnostic Sensitivity (Recall), Specificity, Precision (PPV), Accuracy, and F1-score.
3. **Probability Quality & Calibration**:
   - **Brier Score**: Mean squared error between predicted probabilities and ground truth.
   - **Expected Calibration Error (ECE)**: 10 equal-width bins over $[0, 1]$ (width 0.10). Bin $b$ covers $[b/10, (b+1)/10)$, with the 10th bin covering $[0.90, 1.00]$ inclusive.
4. **Within-Cohort Stratified Bootstrap**:
   - 1,000 resamples per centre, stratified by true target $y$ to preserve exact class counts ($N_{\text{pos}}, N_{\text{neg}}$).
   - 95% confidence intervals derived from the 2.5th and 97.5th percentiles.

---

## 3. Scientific Disclosures & Limitations

- **Within-Cohort Uncertainty Interpretation**: Stratified bootstrap confidence intervals quantify statistical sampling uncertainty *within each observed hospital cohort*, given that institution's specific patient mix and diagnostic referral pattern. They do **not** quantify uncertainty across future unobserved hospitals or alternative health systems.
- **Non-Confirmation of Retrospective Development Data**: Cleveland development results ($N=242$) reflect familiar retrospective development data and must not be interpreted as independent external confirmation.
- **Transportability Limitations**: Three historical clinical cohorts ($N=3$) collected in the late 1980s among patients referred for invasive coronary angiography provide limited empirical evidence regarding generalisation across broader modern healthcare systems, different clinical practice patterns, or primary care screening populations.
- **Regulatory & Clinical Disclaimer**: Open-source research models and metrics are provided for methodological investigation only. They do not constitute, imply, or substitute for clinical validation, ethical clearance, medical device certification, or regulatory approval (e.g. FDA 510(k), CE mark, SaMD) for clinical use.

---
*CardioVanta Phase 17 — Provenance verified against 736 held-out predictions; 61-sample Cleveland locked test set strictly quarantined.*
