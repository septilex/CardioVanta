# Phase 13B.1 — TabICLv2 Feasibility Test

## Overview
An exploratory feasibility test of the `tabicl` package was conducted in an isolated `.venv311` environment to evaluate technical compatibility and behavior with the CardioVanta dataset.

## Installation & Versions
- **Python Version:** 3.11.9 (64-bit)
- **PyTorch Version:** 2.14.0+cpu
- **TabICL Version:** 2.2.0 (via pip install)
- **Model Checkpoint:** `tabicl-classifier-v2-20260212.ckpt` downloaded from Hugging Face Hub (`jingang/TabICL`).
- **Checkpoint Size:** ~110 MB (estimated from Hugging Face cache)

## Hardware & Performance
- **Device Used:** CPU. (The default `pip install torch` installed the CPU-only wheel. Testing on the RTX 3050 4GB GPU would require an explicit `+cu121` index-url install, but the CPU results proved highly efficient).
- **RAM Before Initialization:** 303.5 MB
- **RAM After Inference:** 595.5 MB (Net increase of ~292 MB)
- **VRAM Used:** 0 MB (CPU mode)
- **Inference Latency (49 samples):**
  - First `predict()`: 1.78 seconds
  - `predict_proba()`: 1.61 seconds
  - Repeated `predict_proba()`: 1.65 seconds
- **Compatibility:** Fully compatible. The model gracefully accepted the 13-feature CardioVanta dataset without requiring external categorical encoders or scalers.

## Prediction Outputs
The model successfully outputs binary classification formats:
- **Sample Predictions:** `[1, 0, 0, 1, 0]`
- **Sample Probabilities:** 
  - `[0.154, 0.845]`
  - `[0.943, 0.056]`
  - `[0.949, 0.050]`

## Dataset Size Limitation
The model was fit on a context of just **193 rows** (simulating one fold of the 242-row development set) and predicted on the remaining 49 rows. While it technically runs without error, 193 rows is well below TabICLv2's documented optimal pretraining and context scale (~300 to 1,000,000 samples). It is highly likely that providing a context this small restricts the Foundation Model's ability to extract robust attention mappings. 

## Conclusion: Is a Full Benchmark Worthwhile?
**Technically:** Yes. The model is incredibly lightweight (adding only ~300 MB of RAM usage) and evaluates 49 samples in ~1.6 seconds purely on CPU. It integrates seamlessly into existing Scikit-Learn style pipelines (`fit`, `predict`, `predict_proba`).

**Methodologically:** Borderline. Given the locked 20% test set, our cross-validation context folds are restricted to < 200 rows. While the Foundation Model will not "crash," its performance metrics on a 193-row context may artificially underrepresent its true capability. 

If we proceed with a full benchmark, we must treat it as an exploratory case study on *"How well do Tabular Foundation Models perform in data-starved (N<200) clinical environments?"* rather than a direct attempt to unseat the production Logistic Regression model.
