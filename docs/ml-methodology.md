# ML Methodology

## Dataset & Split
- **Source:** `heart.csv` (SHA-256: `7c3014365675306819510a49ff289efbec1d1a6a666a2dc7652f1547b383d859`)
- **Development Sample Count:** 242
- **Locked Test Sample Count:** 61 (20% of data, completely isolated from training, calibration, threshold selection, robustness, and subgroup analysis)
- **Feature Schema:** 13 features (continuous, binary, categorical). Target is binary.

## Preprocessing
- Continuous features: `StandardScaler`
- Categorical features: `OneHotEncoder(handle_unknown="ignore")`
- Binary features: `passthrough`

## Model Selection & Nested CV
- The methodology utilized nested Cross-Validation to evaluate algorithms.
- **Selected Algorithm:** Logistic Regression
- **Hyperparameters:** `C=0.1`, `class_weight="balanced"`, `solver="lbfgs"`, `random_state=42`
