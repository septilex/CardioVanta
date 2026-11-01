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

## 5. GitHub run
- [x] 5.1 Run the workflow on GitHub (PR #2, run 41289736991). The test steps passed; the quarantine assertion failed in both Python jobs, with two false-positive findings (section 6). No locked or quarantined data was accessed.

## 6. PR #2 CI findings (2026-11-01)
- [x] 6.1 Bytecode caches. Importing `cardiovanta_ml.contracts` from the checkout made Python write `__pycache__/*.pyc.<id>` into the write-protected `cardiovanta_ml/contracts`, and the guard refused it (5 backend, 3 research). Local rehearsals had set `PYTHONDONTWRITEBYTECODE=1`; CI did not. Fix: both guard-enable steps export `PYTHONDONTWRITEBYTECODE=1`. The protected-directory rules are unchanged (regression-tested).
- [x] 6.2 `dir_fd`-relative deletes. Traced with call stacks in a Linux replay: `pip-audit -r requirements.txt` builds a temporary venv and runs `pip install --upgrade pip wheel setuptools` in it. Uninstalling the old `pkg_resources`, and the venv's later cleanup, use `shutil.rmtree`, which on Linux calls `os.rmdir("data", dir_fd=<.../pkg_resources/tests>)`. The guard ignored `dir_fd` and resolved `"data"` against the CWD (the repository), refusing it as the protected `data/` (8 in the pip child, 1 in pip-audit). Fix: the guard resolves `dir_fd`-relative paths (`os.remove`, `os.rmdir`, `os.chmod`, `shutil.rmtree`, `os.rename`, `os.link`, `os.symlink`) against the directory the descriptor refers to. An unresolvable descriptor keeps the stricter CWD resolution. This also closes the converse gap, where a `dir_fd`-relative delete inside a protected directory was resolved against the CWD and allowed. No exception was added for `data/`, and `rmdir` is not allowed broadly (regression-tested on Linux against the old and new guard).

## 7. Deployment safety (2026-11-01)
- [x] 7.1 Vercel upload exclusions (commit `ea331f2`). `.vercelignore` lists the seven locked-derived `experiments/` outputs by exact, root-anchored path; `experiments/` as a whole is still uploaded. The simulated CLI 59.26.0 upload drops from 453 to 446 files, exactly these seven, and every runtime file is still uploaded. Regression test: `test_vercelignore_excludes_locked_derived_results`.
- [x] 7.2 Deployment-job sparse checkout. `deploy` and `verify-production` use the verification jobs' 17-pattern sparse checkout, and every later step is unchanged. The three verification jobs are byte-identical. Verified on a disposable partial clone: the 18 protected files are absent and their blobs were never fetched. Regression test: every job in `verify.yml` that checks out the repository uses the quarantine patterns. Both jobs run only on a push to `main`, so pull-request CI cannot exercise them.
