# Limitations

1. **Small Sample Size:** The development dataset contains only 242 samples, and the locked test set contains 61.
2. **Clinical Applicability:** The system lacks an authoritative clinical threshold. All predictions and candidate thresholds are strictly mathematical descriptors.
3. **Explanations != Causality:** Global and local explanations highlight linear log-odds associations. They do not demonstrate or imply medical causality.
4. **Subgroup Estimability:** Statistical stability cannot be estimated for subgroups smaller than 20 patients (e.g., `cp=3`, `restecg=2`, `slope=0`). Extrapolating performance to these demographics is unreliable.
5. **Development Range:** Inputs that fall outside the continuous min/max bounds observed in the training data produce undefined reliability, explicitly flagged by the `DevelopmentRangeWarning`.
