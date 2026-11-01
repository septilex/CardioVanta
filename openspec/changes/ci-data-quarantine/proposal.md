# Proposal: CI Research-Data Quarantine

## Why
`.github/workflows/verify.yml` ran `pytest tests/` in a required `research-data-tests` job, which did three things it should not:
- **Read the locked rows.** It read `data/raw/heart.csv`, the only file that contains the 61 locked Cleveland observations. Several suites also rebuild the split from it.
- **Read other research data.** It read the development indices, the external cohorts and locked-derived research results.
- **Retrained and overwrote results.** Some suites retrain models, and `run_phase4b()` rewrites `reports/phase4b_*`.

This conflicts with the standing rule that the locked observations are never opened, parsed or loaded. Nothing enforced the "synthetic only" claim of the production job either.

## What Changes
- **Shared policy** in `scripts/ci/data_quarantine.py`:
  - **Denied:** the locked source (`data/raw/heart.csv`), 14 locked-derived outputs (classified from their producing code, never opened), and all other `data/` files except the UCI codebook text.
  - **Write-protected:** research results, artifacts, the contract and data.
- **Runtime guard.** An irreversible `sys.addaudithook` hook, activated through `scripts/ci/quarantine_site/sitecustomize.py`, refuses and logs Python-level access, including in subprocesses. CI fails if the log is not empty.
- **Sparse checkout.** Quarantined jobs use a non-cone sparse checkout, so denied files are never on the runner. An absence check and a pattern check enforce it.
- **Static guard.** `scripts/ci/check_data_access.py` flags any unregistered direct reference to quarantined data. The registry is `scripts/ci/data_access_registry.json`, with a role for every referencing file.
- **Explicit test classification** (`scripts/ci/test_classification.py`). Every test module is `ci_safe`, `ci_safe_research_deps` or `research_data`, based on runs under the guard in a checkout without quarantined files. CI runs exactly the safe classes, and unclassified modules fail CI.
- **Workflow change.** `research-data-tests` is replaced by `quarantined-research-tests`. All other safe checks are kept: backend synthetic tests, contract generation, artifact integrity, package and wheel verification, TypeScript/Jest/Next build, and pip/npm audits.
- **Tests:** `tests/test_data_quarantine.py`.

## Non-goals
- No change to production code, artifacts, the registry, the contract, the API, the frontend, research results or the deploy jobs.
- No data file is opened, moved or deleted.
- `research_data` suites are not run anywhere in CI. Running them needs an explicit, separate decision.
