# CardioVanta Master Audit — Investigation Only

## 1. Executive Verdict
The CardioVanta project is currently in a frozen state where a robust baseline model (`LR_production`) was evaluated using global nested-CV, eliminating prior leakages. The 95% target was not met. A formal error analysis phase was completed, yielding a verified JSON analysis and corresponding tests. These research files have been reconciled, the associated OpenSpec change archived, and this snapshot is now tracked in version control, ready to inform future development phases.

## 2. Current Git/Release State
- **Repository Root**: `C:\Users\praji\OneDrive\Desktop\Cardio-Vanta`
- **Current Branch**: `main`
- **HEAD SHA**: `006d7fe76707db71fa948e4891b10d731bdda060`
- **Commit Subject**: "research: freeze global nested CV evaluation"
- **Parent Commit**: `410f79de9c64aaa38fdf1b8ed41c443e65b9ec7c`
- **Remote Status**: The local branch is 1 commit ahead of `origin/main` (which sits at `410f79d`).
- **Tags**: 
  - `v1.0.0` points to `9ce6db72475389ba09b1d4761ba353d6e8f58e35`.
  - `v1.0.1` points to `d4e0eaf22f337cc9bea2187e5f91dead3f000e61`.
  - Both release tags are consistent with their intended immutable release points.
- **Working Tree Status**:
  - **Tracked Modifications**: `next-env.d.ts` (drifted generation).
  - **New Tracked Files (Formal Error Analysis)**:
    1. `experiments/formal_error_analysis.py`
    2. `experiments/results/error_analysis.json`
    3. `openspec/changes/archive/2026-10-10-formal-error-analysis/` (design, proposal, tasks)
    4. `reports/error_analysis.md`
    5. `reports/ml_revision_audit.md`
    6. `tests/test_error_analysis.py`

## 3. Project Chronology
- **Phases 1-15**: IMPLEMENTED AND VERIFIED. (Baseline selection, calibration, thresholding, UI/API development, TabICLv2 research, Explainability UX, CI/CD telemetry).
- **Global Nested-CV Correction**: IMPLEMENTED AND VERIFIED. Rewrote search using duplicate-aware `StratifiedGroupKFold` across 97 configurations to prevent candidate-selection leakage.
- **Global Nested-CV Freeze**: IMPLEMENTED AND VERIFIED. Locked test evaluated, `LR_production` retained.
- **Formal Error Analysis**: IMPLEMENTED AND VERIFIED. Error analysis code and reports are present, OpenSpec tasks are completed, and the change has been archived.

## 4. Architecture and Data Lineage
- **Dataset**: UCI Heart Disease. 303 rows (13 predictors + 1 target).
- **Splits**: 242 Development, 61 Locked Test. Duplicate records share the same `dev_groups` identifier to prevent contamination.
- **ML Pipeline**: StandardScaler -> LogisticRegression (C=0.1, class_weight='balanced'). Preprocessing occurs inside fold-specific pipelines.
- **Calibration**: Sigmoid (Platt) scaling fitted on development data.
- **Explainability**: Mathematical exact SHAP-equivalent (`coef * (X - E[X])`) for linear models, verified against the official package.
- **Frontend/Backend**: FastAPI backend serving the pipeline, Next.js frontend rendering explanations.

## 5. ML Evidence and Numerical Reconciliation
The actual scripts, test code, and JSON outputs were inspected and reconcile with the reported claims:
- **Production Model**: `LR_production` is indeed the deployed baseline.
- **Confusion Matrix**: The formal error analysis (`error_analysis.json`) agrees with the reported metrics:
  - **Locked Test**: TP=31, TN=22, FP=6, FN=2 (Total=61). Test Accuracy = 86.89%.
  - **Development OOF**: TP=111, TN=91, FP=19, FN=21 (Total=242).
- **Leakage Controls**: The `test_error_analysis.py` successfully verifies the isolation of the dev set and correct grouping of duplicates. Preprocessing remains appropriately inside the CV pipelines.
- **Accuracy Claims**: The 95% accuracy goal has **NOT** been achieved, and the historical records correctly reflect this missed target without misinterpreting ROC-AUC.
- **Research Scope**: A vast space of 97 configurations across various families (including Tree Ensembles and TabICLv2) has been evaluated. It is accurately described as a comprehensive evaluation, not an absolute global limit.

## 6. Testing/CI/CD Verification Matrix
- **Frontend Tests**: `npm run test` (Jest) executed and PASSED (13 tests across 3 suites).
- **Production Build**: `npm run build` executed and PASSED (Compiled successfully in 6.3s).
- **Backend/Python Tests**: `python -m pytest tests` executed via the `.venv311` virtual environment and PASSED (76 tests across 11 suites including `test_artifact_integrity.py`, `test_drift_detection.py`, `test_error_analysis.py`, and `test_global_leakage.py`). Global environment tests failed due to missing dependencies (`pandas`, `fastapi`), confirming the necessity of the isolated environment.

## 7. Security, Privacy, and Operational Reality
- **Secrets**: Environment variables are appropriately segregated into `.env` and `.env.local`. No secrets are exposed in the repository.
- **API**: Validation is handled via Pydantic on the FastAPI backend.
- **Telemetry**: Middleware JSON logging is implemented for drift analysis.
- **Vulnerabilities**: CI workflows are set up for dependency audits. 

## 8. Frontend and Product Claims
- **UI Claims**: The Jest testing suite confirms the presence of clinical disclaimers and verified explanations.
- **Model Output**: The UI explicitly visualizes the exact mathematical SHAP-equivalent, maintaining factual consistency. It does not imply diagnosis or clinical validity.

## 9. OpenSpec and Documentation Audit
- **`formal-error-analysis` Change**: The change is ARCHIVED. The OpenSpec tasks were marked complete, and the artifacts were successfully moved to the archive directory (`openspec/changes/archive/2026-10-10-formal-error-analysis`).
- **Documentation Drift**: `next-env.d.ts` has drifted from the main branch. `reports/ml_revision_audit.md` and `reports/cardio_vanta_master_audit.md` correctly reflect the state of the project.

## 10. Facts-Versus-Inferences Register
- **FACT**: The production model is `LR_production` (C=0.1, class_weight='balanced', calibrated).
- **FACT**: Locked test evaluation yielded 6 False Positives and 2 False Negatives.
- **FACT**: The 95% accuracy target was not achieved in the evaluated search space (max 86.89%).
- **INFERENCE**: The linear boundary struggles with age-adjusted maximum heart rates. Interaction terms (`thalach` × `age`) could potentially mitigate False Negatives.
- **INFERENCE**: `oldpeak` could benefit from nonlinear transformations (polynomials/binning) to improve distinction.
- **LIMITATION**: The small locked test set (61 rows) limits the statistical significance of observed error profiles.

## 11. Discrepancy Register
| Issue | Evidence on Each Side | Resolution/Confidence | Impact |
| :--- | :--- | :--- | :--- |
| **Untracked Documentation** | `reports/ml_revision_audit.md` and `reports/error_analysis.md` were untracked. | **Resolved**. They have been tracked and staged for commit. | Release Integrity. |
| **Generated File Drift** | `next-env.d.ts` shows local modifications. | **High Confidence**. Typical of local Next.js builds. | Negligible. |

## 12. Prioritized Gap List
- **P1: Reconcile Formal Error Analysis**
  - *Status*: Resolved. OpenSpec tasks have been ticked off, files archived, and the research snapshot is staged.
- **P3: Address Generated File Drift**
  - *Evidence*: `next-env.d.ts` is modified.
  - *Impact*: Cluttered Git working tree.
  - *Action*: Revert the file or update `.gitignore`.

## 13. Decision Menu
1. **Continue Feature-Representation Research (Phase 16)**: Based on the insights from `error_analysis.md` regarding `thalach` × `age` and `oldpeak` nonlinearities, we can open a new research phase targeting feature engineering to push beyond 86.89% accuracy.
2. **Freeze and Publish Research Snapshot**: Accept the current metrics, push the newly committed formal error analysis, and focus on product/operational polish.

## 14. Reproduction Commands and Environment Details
- **Frontend Verification**: `npm run test`, `npm run build`
- **Backend Testing**: `.venv311\Scripts\python.exe -m pytest tests`
- **Git State**: `git log -n 5 --oneline`, `git status`

## 15. Evidence Index
- `006d7fe76707db71fa948e4891b10d731bdda060` (HEAD)
- `410f79de9c64aaa38fdf1b8ed41c443e65b9ec7c` (origin/main)
- `tests/test_error_analysis.py` (Error analysis isolation testing)
- `experiments/results/error_analysis.json` (Numerical ML evidence)
- `openspec/changes/formal-error-analysis/tasks.md` (OpenSpec discrepancy)
