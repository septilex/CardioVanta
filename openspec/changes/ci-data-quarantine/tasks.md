# Tasks

## 1. Analysis
- [x] 1.1 Trace `verify.yml` statically, along with every test module, script and output producer that touches `heart.csv`, the split, external cohorts or locked-derived results. Producers were classified by their code only; no data file was opened.

## 2. Implementation
- [x] 2.1 Shared policy and runtime guard (`scripts/ci/data_quarantine.py`, `scripts/ci/quarantine_site/sitecustomize.py`).
- [x] 2.2 Static guard and registry (`scripts/ci/check_data_access.py`, `scripts/ci/data_access_registry.json`).
- [x] 2.3 Explicit test classification (`scripts/ci/test_classification.py`), backed by quarantined runs.
- [x] 2.4 Workflow: sparse checkouts, guard activation, verification steps, classified test execution, clean-log assertions, and `quarantined-research-tests` replacing `research-data-tests`.
- [x] 2.5 Guard tests (`tests/test_data_quarantine.py`).

## 3. Verification
- [x] 3.1 Sparse-checkout patterns verified on a scratch clone (18 files skipped, codebook present).
- [x] 3.2 Both quarantined CI jobs rehearsed in a scratch copy with no quarantined files, with zero refused accesses.
- [x] 3.3 OpenSpec validation and `git diff --check`; artifacts and research results unchanged.

## 4. Horizon 0 housekeeping (2026-11-01)
- [x] 4.1 Redact the raw patient-level row in `reports/cardio_vanta_master_audit.md` (the duplicated development row and its indices); the duplicate-group finding is preserved. Regression tests scan readable reports and docs for patient-level rows. The row remains in Git history from `cb80d11`, and history is not rewritten.
- [x] 4.2 Pin the Vercel CLI in the deploy job to `59.26.0`, matching `vercel-linux-build.yml`, with a regression test.
- [x] 4.3 Triggers: pull requests into `main` run every verification job unconditionally. Deployment is gated to `push` on `main` (`environment: production`), and `verify-production` depends on it. Regression-tested.

## 5. Open
- [ ] 5.1 Run the workflow on GitHub. Not done: it needs a push, which was not authorised.
