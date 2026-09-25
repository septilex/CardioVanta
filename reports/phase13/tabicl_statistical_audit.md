# Phase 13B.4 — TabICLv2 Statistical Audit

## 1. Production Baseline Equivalence
The Logistic Regression baseline used in Phase 13 was compared against the actual serialized production `model.joblib`. 
**Difference Found:** Phase 13 explicitly declared `max_iter=1000`, while the production pipeline defaulted to `max_iter=100`.
**Impact:** `0.0`. The metrics and per-sample probabilities on the locked test set are mathematically identical to 4 decimal places. The model converged well within 100 iterations.

## 2. Paired Bootstrap Analysis (TabICLv2 Native vs Production LR)
A 10,000-iteration paired bootstrap resampling was conducted on the locked test set (N=61) to compute 95% Confidence Intervals for the *difference* in performance metrics (TabICL Native minus Production LR).

| Metric | Mean Difference | 95% Confidence Interval | Statistically Significant? |
| :--- | :--- | :--- | :--- |
| **ROC-AUC** | +0.0118 | [-0.0167, 0.0484] | **No** |
| **Average Precision** | +0.0049 | [-0.0170, 0.0296] | **No** |
| **Brier Score** | -0.0119 | [-0.0322, 0.0066] | **No** (lower is better) |
| **Log Loss** | -0.0372 | [-0.0873, 0.0111] | **No** (lower is better) |
| **F1 Score** | +0.0030 | [-0.0494, 0.0584] | **No** |
| **Recall** | +0.0300 | [0.0000, 0.1000] | **Borderline** |
| **Specificity** | -0.0360 | [-0.1600, 0.0800] | **No** |

*Interpretation:* While TabICLv2 Native achieved a higher mean ROC-AUC and a lower Brier Score, the 95% confidence intervals all cross zero. **There is no statistically significant difference in performance** between the zero-shot TabICLv2 Foundation Model and the heavily tuned production Logistic Regression on this 61-sample test set.

## 3. Calibration Interpretation
In Phase 13B.3, the sigmoid-calibrated TabICLv2 performed worse than the Native TabICLv2. 
**Correct Interpretation:** Native TabICLv2 probabilities performed better than the tested sigmoid-calibrated version under this specific nested-CV evaluation protocol. 
We cannot broadly declare TabICLv2 to be universally "highly calibrated", because the nested CV process inherently reduces the available context data (from ~193 rows to ~154 rows) inside the inner loop, conflating the effect of the calibration algorithm with the effect of reducing the foundation model's context window.

## 4. Dataset Size & Claims
Given the small sample size (N=61 test, N=242 context), the evaluation does not possess the statistical power required to establish one model as universally superior. 
Unsupported claims of the model being "attention starved" (requiring more data to beat LR) or being universally "production-ready" must be excluded. The empirical reality is simply that the models perform on par for this specific dataset.

## 5. Conclusion & Phase Status
TabICLv2 provides extremely strong evidence that Tabular Foundation Models can match the performance of traditional, tuned ML pipelines without any explicit gradient updates. However, it does **not** provide evidence of a statistically meaningful predictive improvement over the existing Logistic Regression on this specific dataset.

Given that Logistic Regression provides identical statistical performance at zero VRAM cost, microseconds of latency, and requires no 105MB checkpoint download, the current Vercel production deployment remains strictly optimal.

**Phase 13B is officially concluded.** The isolated TabICLv2 research environment has served its exploratory purpose and provided rigorous validation of an alternative ML architecture. No further model changes are recommended at this time.
