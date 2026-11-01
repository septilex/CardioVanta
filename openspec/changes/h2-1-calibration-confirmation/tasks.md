# Tasks

## 1. Pre-registration
- [x] 1.1 Write and validate the proposal and design before any H2.1 code or results: the endpoint, direction, intervals, multiplicity, acceptance criteria and the external-cohort exclusion with reasons.

## 2. Implementation
- [x] 2.1 Implement `experiments/h2_1_calibration_confirmation.py`: the R4 loader, arms A and C, 20-repeat nested CV with H2-disjoint seeds, the repeat-level paired bootstrap, the pre-registered verdict, and the recorded external exclusion.
- [x] 2.2 Add synthetic regression tests (`tests/test_h2_1_calibration_confirmation.py`). Acceptance: the tests pass with no dataset read. Result: 7/7 pass.

## 3. Execution
- [x] 3.1 Run the experiment on the 242 development rows. Acceptance: exit 0 and exactly 242 rows used. Result: met.
- [x] 3.2 Run it a second time. Acceptance: identical result content. Result: identical (`70b6b136…`).
- [x] 3.3 Verify production isolation. Acceptance: the artifact integrity check passes.

## 4. Reporting
- [x] 4.1 Write `reports/h2_1_calibration_confirmation.md`, covering the verdict per criterion, secondary endpoints with adjusted intervals, the external exclusion and limitations.

## Outcome
Confirmed: all four pre-registered criteria pass. Δslope is −0.271 [−0.341, −0.216] and negative in 20/20 repeats; ΔAUC is −0.0003; arm C's slope is 1.003. The secondary endpoints are directionally consistent but not supported at the adjusted level. This is internal replication on the same 242 patients, and production is unchanged.
