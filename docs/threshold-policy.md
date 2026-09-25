# Threshold Policy

## Clinical Operating Points
A statistically selected threshold is **NOT** automatically a clinically validated decision threshold.

**Key Policies:**
1. Production inference must return the calibrated probability. Applying a threshold is strictly optional.
2. Any threshold provided is a mathematical operating point on the pooled development dataset, not a clinical diagnosis. 
3. No validated production threshold exists for this system (`authoritative_clinical_threshold: null`).

## Descriptive Mathematical Candidates (Development OOF)
- **Default (0.50):** F1 = 0.8496
- **Youden's J (0.46):** F1 = 0.8686
- **Max F1 (0.43):** F1 = 0.8693
