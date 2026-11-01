# Design: CI Research-Data Quarantine

## Threat model
The goal is to prevent *accidental* access to the locked Cleveland observations, and to research data generally, in default CI. Examples include a broad test collection, a new test that rebuilds the split, or a helper that reads `RAW_DATA_PATH`. A deliberately malicious change to the workflow itself is out of scope; branch protection and review address that.

## Layers
1. **Absence (strongest).** A non-cone sparse checkout (`/*`, `!/data/*`, re-include the codebook, `!/<each locked-derived file>`) keeps denied files off the runner.
   - It was verified with `git sparse-checkout --no-cone` on a scratch clone: exactly 18 files were skipped (4 data files and 14 locked-derived files), the codebook was present and artifacts were intact.
   - `--assert-absent` checks file names only (`os.path.lexists`) and fails if any denied file is present.
2. **Runtime guard.** An audit hook on `open`, `os.remove`, `os.rename`, `shutil.copyfile`, `shutil.rmtree` and related events.
   - It raises `PermissionError` and appends a JSON-lines record.
   - It is activated by `sitecustomize` (`CARDIOVANTA_DATA_QUARANTINE=1`, with `PYTHONPATH` including `scripts/ci/quarantine_site`), so child Python processes inherit it.
   - `--assert-clean-log` runs with `if: always()`, so an attempt swallowed by a test still fails CI.
3. **Static guard.** An AST scan for non-docstring literals naming protected resources, or uses of `load_locked_test`.
   - Every referencing file must be registered with a role: `research_data_access`, `negative_assertion` or `path_reference`.
   - Unregistered references, stale entries, and `ci_safe` tests with a `research_data_access` role all fail.
4. **Classification.** An explicit `tests/` and `backend/tests/` manifest. CI runs `pytest $(test_classification.py --list ci_safe …)`, never a directory. Completeness is checked.

## Classification evidence (2026-11-01)
Each module was run in a scratch copy containing no quarantined files, with the guard active. The original checkout was protected as well (`CARDIOVANTA_QUARANTINE_EXTRA_ROOTS`).
- **Backend suite:** 512 passed, 0 refused.
- **Safe research tests:** R4, H2, H2.1, R5, R6, R7, R7-C1, monitoring and artifact integrity passed with 0 refusals. `test_phase3` passed with 0 refusals on the research stack.
- **Research-data tests:** 19 modules, each with a recorded refused access (`heart.csv`, `dev_indices.json`, `hungarian.data` or locked-derived results) or a raw-data dependency.

## Known limitations
- Audit hooks do not see opens made directly by C libraries or non-Python processes. Layer 1 covers these in CI.
- Interpreters started with `-I` or `-E` (for example the clean-venv wheel verification) do not load `sitecustomize`. That step reads only artifacts.
- `deploy` and `verify-production` use the same 17-pattern sparse checkout as the verification jobs (2026-11-01), so the 18 protected files are absent from the deployment runners too. A regression test requires this for every job in `verify.yml` that checks out the repository.
- `vercel-linux-build.yml` (manual, never deploys) still uses a full checkout and runs no tests. The Vercel CLI uploads nothing that `.vercelignore` excludes: `data/`, `reports/`, and the seven locked-derived `experiments/` outputs, which are listed by exact path (regression-tested).
- Locked-derived classification relies on reading the producing code. A newly produced locked-derived file must be added to the policy; new Python references to it are caught by the static guard.
