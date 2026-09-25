# Phase 13B.2 — TabICLv2 RTX 3050 GPU Feasibility Test

## Overview
A follow-up test of the `tabicl` Foundation Model to measure performance, memory footprints, and mathematical consistency when running purely on an **NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM)**.

## Environment & Versions
- **Python Version:** 3.11.9 (64-bit)
- **PyTorch Version:** 2.5.1+cu121 (Upgraded from CPU to CUDA 12.1 wheel)
- **TabICL Version:** 2.2.0
- **Device Detected:** CUDA (`NVIDIA GeForce RTX 3050 Laptop GPU`)
- **Model Checkpoint:** `tabicl-classifier-v2-20260212.ckpt` 
- **Checkpoint Size:** 105.25 MB (Confirmed via Hugging Face cache)

## Memory Usage (GPU & RAM)
TabICLv2 is remarkably parameter-efficient and places virtually zero stress on the 4GB limit of the RTX 3050.

- **VRAM Before Init:** 0.0 MB
- **VRAM After Init:** 0.0 MB (Lazy loading observed)
- **VRAM After Inference:** 116.24 MB
- **Peak VRAM During Inference:** **211.74 MB**
- **RAM After Inference:** 1194.6 MB (A typical spike driven primarily by CUDA context initialization, safe for local environments).

*Note: Peak VRAM of 211 MB means the RTX 3050 (4096 MB) is operating at just ~5% capacity.*

## Performance (GPU vs CPU Latency)
In-context learning models process all training and test data in a single forward pass, heavily benefiting from parallelization. 
*(Tested on context N=193, predicting N=49)*

| Metric | CPU (Previous) | GPU (RTX 3050) | Speedup |
| :--- | :--- | :--- | :--- |
| **First `predict()`** | 1.78 sec | 0.51 sec | **3.5x** |
| **`predict_proba()`** | 1.61 sec | 0.18 sec | **8.9x** |
| **Repeated `predict_proba()`**| 1.65 sec | 0.19 sec | **8.7x** |

**Conclusion:** The GPU delivers a near 9x acceleration in probability inference.

## Numerical Consistency
Comparing the softmax probability outputs of the CPU and GPU passes demonstrates perfect stability within FP32 floating-point precision bounds:

**Sample 1 (CPU):** `[0.1543687, 0.8456312]`
**Sample 1 (GPU):** `[0.1543690, 0.8456310]`

**Sample 2 (CPU):** `[0.9437932, 0.0562067]`
**Sample 2 (GPU):** `[0.9437933, 0.0562066]`

Binary hard predictions (`1, 0, 0, 1, 0`) perfectly match.

## Final Assessment for Full Benchmark
The NVIDIA RTX 3050 4GB is **exceptionally suitable** for the full TabICLv2 benchmark. 

- **Stability:** Zero Out-Of-Memory (OOM) or CUDA errors occurred.
- **Overhead:** Peak VRAM was 211 MB, leaving over 3.8 GB of headroom for K-Fold parallelization or vastly larger context windows if needed.
- **Latency:** ~180 milliseconds per fold means an inner/outer cross-validation suite (e.g., 25 folds total) will execute in less than 5 seconds on the GPU, compared to ~45 seconds on the CPU.
