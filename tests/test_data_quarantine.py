"""
Tests for the CI research-data quarantine (runtime guard, static guard, test classification, workflow).

Safety: runtime tests only ever target a temporary FAKE root (registered through
CARDIOVANTA_QUARANTINE_EXTRA_ROOTS) holding synthetic files. The real protected files are never
opened, even if the guard were broken.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "scripts" / "ci" / "quarantine_site"
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dq = _load("dq_under_test", "scripts/ci/data_quarantine.py")
sg = _load("sg_under_test", "scripts/ci/check_data_access.py")
tc = _load("tc_under_test", "scripts/ci/test_classification.py")


# --- Policy decisions (pure; nothing is opened) -------------------------------------

@pytest.mark.parametrize("rel,reason", [
    ("data/raw/heart.csv", "locked_source"),
    ("experiments/results/error_analysis.json", "locked_derived"),
    ("reports/phase2c_final_evaluation.json", "locked_derived"),
    ("reports/cardio_vanta_master_audit.md", "locked_derived"),
    ("data/processed/dev_indices.json", "research_data"),
    ("data/external/raw/hungarian.data", "research_data"),
    ("data/anything/new_file.csv", "research_data"),
])
def test_reads_of_protected_paths_are_denied(rel, reason):
    record = dq.decide("open", (str(ROOT / rel), "r", 0))
    assert record is not None and record["reason"] == reason


@pytest.mark.parametrize("rel", [
    "data/external/raw/heart-disease.names",            # codebook documentation
    "experiments/results/r7_unverified_feature_ablation.json",
    "reports/phase17_multicenter_validation.md",
    "artifacts/model/reference_predictions.csv",          # development-row predictions (production artifact)
    "cardiovanta_ml/contracts/feature_schema.v2.json",
])
def test_reads_of_allowed_paths_pass(rel):
    assert dq.decide("open", (str(ROOT / rel), "r", 0)) is None


@pytest.mark.parametrize("rel", ["experiments/results/new.json", "artifacts/model/model.joblib",
                                 "reports/x.md", "cardiovanta_ml/contracts/feature_schema.v2.json"])
def test_writes_into_protected_directories_are_denied(rel):
    assert dq.decide("open", (str(ROOT / rel), "w", 0))["reason"] == "write_protected"
    assert dq.decide("open", (str(ROOT / rel), None, os.O_WRONLY | os.O_CREAT))["reason"] == "write_protected"
    assert dq.decide("os.remove", (str(ROOT / rel), None))["reason"] == "write_protected"


def test_rename_copy_and_unrelated_paths(tmp_path):
    assert dq.decide("os.rename", (str(tmp_path / "a"), str(ROOT / "artifacts" / "model" / "x"), None, None))["reason"] == "write_protected"
    assert dq.decide("shutil.copyfile", (str(ROOT / "data" / "raw" / "heart.csv"), str(tmp_path / "copy.csv")))["reason"] == "locked_source"
    assert dq.decide("open", (str(tmp_path / "scratch.csv"), "w", 0)) is None
    assert dq.decide("open", (3, "r", 0)) is None                       # file descriptors are not paths
    assert dq.decide("open", (os.fsencode(str(ROOT / "data" / "raw" / "heart.csv")), "rb", 0))["reason"] == "locked_source"
    assert dq.decide("os.listdir", (str(ROOT / "data"),)) is None       # listing names is not reading data


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive file system")
def test_windows_case_variants_are_denied():
    assert dq.decide("open", (str(ROOT / "DATA" / "Raw" / "HEART.CSV"), "r", 0))["reason"] == "locked_source"


# --- Runtime guard in real interpreters (fake root only) --------------------------------

@pytest.fixture()
def fake_root(tmp_path):
    root = tmp_path / "fake_checkout"
    (root / "data" / "raw").mkdir(parents=True)
    (root / "data" / "raw" / "heart.csv").write_text("synthetic,not,real\n1,2,3\n", encoding="utf-8")
    (root / "experiments" / "results").mkdir(parents=True)
    return root


def _run(code, fake_root, log, tmp_path, quarantine=True, cwd=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CARDIOVANTA_")}
    env.update({"PYTHONPATH": str(SITE), "CARDIOVANTA_QUARANTINE_EXTRA_ROOTS": str(fake_root),
                "CARDIOVANTA_QUARANTINE_LOG": str(log)})
    if quarantine:
        env["CARDIOVANTA_DATA_QUARANTINE"] = "1"
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env, cwd=cwd or tmp_path,
                          capture_output=True, text=True, timeout=120)


def test_guard_blocks_python_pandas_and_numpy_reads(fake_root, tmp_path):
    log = tmp_path / "q.jsonl"
    code = f"""
        import sys, numpy as np, pandas as pd
        target = r"{fake_root / 'data' / 'raw' / 'heart.csv'}"
        results = []
        for name, fn in [("open", lambda: open(target).read()), ("pandas", lambda: pd.read_csv(target)),
                         ("numpy", lambda: np.loadtxt(target, delimiter=",", skiprows=1)),
                         ("os.open", lambda: __import__("os").open(target, 0))]:
            try:
                fn(); results.append(name + ":READ")
            except PermissionError as e:
                results.append(name + ":DENIED" if "data quarantine" in str(e) else name + ":OTHER")
        print(" ".join(results))
    """
    r = _run(code, fake_root, log, tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["open:DENIED", "pandas:DENIED", "numpy:DENIED", "os.open:DENIED"]
    records = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(records) == 4 and {x["reason"] for x in records} == {"locked_source"}


def test_guard_is_inherited_by_subprocesses_and_swallowed_attempts_are_logged(fake_root, tmp_path):
    log = tmp_path / "q.jsonl"
    code = f"""
        import subprocess, sys
        child = "try:\\n    open(" + repr({str(fake_root / 'data' / 'raw' / 'heart.csv')!r}) + ")\\nexcept PermissionError:\\n    pass\\n"
        subprocess.run([sys.executable, "-c", child], check=True)
    """
    r = _run(code, fake_root, log, tmp_path)
    assert r.returncode == 0, r.stderr
    assert len(log.read_text().splitlines()) == 1                       # swallowed in the child, still logged
    assert dq.main(["--assert-clean-log", str(log)]) == 1
    assert dq.main(["--assert-clean-log", str(tmp_path / "absent.jsonl")]) == 0


def test_guard_blocks_writes_into_results(fake_root, tmp_path):
    log = tmp_path / "q.jsonl"
    r = _run(f"open(r'{fake_root / 'experiments' / 'results' / 'x.json'}', 'w')", fake_root, log, tmp_path)
    assert r.returncode != 0 and "write_protected" in r.stderr
    assert not (fake_root / "experiments" / "results" / "x.json").exists()


def test_guard_inactive_without_flag(fake_root, tmp_path):
    r = _run(f"print(len(open(r'{fake_root / 'data' / 'raw' / 'heart.csv'}').read()))", fake_root,
             tmp_path / "q.jsonl", tmp_path, quarantine=False)
    expected = len((fake_root / "data" / "raw" / "heart.csv").read_text(encoding="utf-8"))   # synthetic fake file only
    assert r.returncode == 0 and r.stdout.strip() == str(expected)


def _dir_fd_resolvable() -> bool:
    if os.name == "nt" or os.rmdir not in os.supports_dir_fd:
        return False
    fd = os.open(".", os.O_RDONLY)
    try:
        return dq._fd_dir(fd) is not None
    finally:
        os.close(fd)


@pytest.mark.skipif(not _dir_fd_resolvable(), reason="dir_fd deletes are POSIX-only (resolved via /proc or F_GETPATH)")
def test_dir_fd_relative_deletes_resolve_to_the_descriptor_directory(fake_root, tmp_path, monkeypatch):
    # PR #2 CI finding: shutil.rmtree on Linux calls os.rmdir("data", dir_fd=<parent>) while cleaning a
    # temporary venv; the guard resolved "data" against the CWD (the repo) and refused it.
    # Pure decide() calls; the only real opens are read-only opens of directories the policy allows
    # (this process may itself be guarded in CI, with the fake root registered below).
    monkeypatch.setenv(dq.ENV_EXTRA_ROOTS, str(fake_root))
    outside = tmp_path / "venv" / "tests"
    (outside / "data").mkdir(parents=True)
    monkeypatch.chdir(fake_root)                              # CWD-relative "data" would be fake_root/data
    fds = []
    try:
        out_fd = os.open(str(outside), os.O_RDONLY); fds.append(out_fd)
        assert dq.decide("os.rmdir", ("data", out_fd)) is None                     # not the protected data/
        assert dq.decide("os.remove", ("data", out_fd)) is None
        assert dq.decide("shutil.rmtree", ("data", out_fd)) is None
        # no descriptor (-1 / None): CWD-relative resolution and the protected-directory rule are unchanged
        assert dq.decide("os.rmdir", ("data", -1))["reason"] == "write_protected"
        assert dq.decide("shutil.rmtree", ("data", None))["reason"] == "write_protected"
        # the converse is now caught: dir_fd-relative operations INSIDE protected directories
        monkeypatch.chdir(tmp_path)
        data_fd = os.open(str(fake_root / "data"), os.O_RDONLY); fds.append(data_fd)
        res_fd = os.open(str(fake_root / "experiments" / "results"), os.O_RDONLY); fds.append(res_fd)
        assert dq.decide("os.rmdir", ("raw", data_fd))["reason"] == "research_data"      # data/raw
        assert dq.decide("os.remove", ("raw/heart.csv", data_fd))["reason"] == "locked_source"
        assert dq.decide("os.chmod", ("x.json", 0o777, res_fd))["reason"] == "write_protected"
        assert dq.decide("os.rename", ("a", "x.json", -1, res_fd))["reason"] == "write_protected"
        assert dq.decide("os.link", ("a", "x.json", -1, res_fd))["reason"] == "write_protected"
        assert dq.decide("os.symlink", ("anything", "x.json", res_fd))["reason"] == "write_protected"
    finally:
        for fd in fds:
            os.close(fd)


def test_guard_allows_rmtree_of_unrelated_tree_containing_data_dir(fake_root, tmp_path):
    # End to end in a guarded interpreter whose CWD is the (fake) checkout, as in CI: deleting a temporary
    # tree that happens to contain a "data" directory succeeds and logs nothing, while deleting the
    # protected data/ is still refused and logged.
    scratch = tmp_path / "scratch_venv" / "site-packages" / "pkg" / "tests"
    (scratch / "data" / "nested").mkdir(parents=True)
    (scratch / "data" / "nested" / "f.txt").write_text("synthetic", encoding="utf-8")
    log = tmp_path / "q.jsonl"
    code = f"""
        import shutil
        shutil.rmtree(r"{tmp_path / 'scratch_venv'}")
        try:
            shutil.rmtree(r"{fake_root / 'data'}")
            print("PROTECTED:REMOVED")
        except PermissionError as e:
            print("PROTECTED:DENIED" if "data quarantine" in str(e) else "PROTECTED:OTHER")
    """
    r = _run(code, fake_root, log, tmp_path, cwd=fake_root)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["PROTECTED:DENIED"]
    assert not (tmp_path / "scratch_venv").exists() and (fake_root / "data" / "raw" / "heart.csv").exists()
    records = [json.loads(l) for l in log.read_text().splitlines()]
    assert [(x["event"], x["path"]) for x in records] == [("shutil.rmtree", "data")]


def test_present_denied_files_lists_names_without_opening(fake_root):
    (fake_root / "data" / "external" / "raw").mkdir(parents=True)
    (fake_root / "data" / "external" / "raw" / "heart-disease.names").write_text("codebook", encoding="utf-8")
    (fake_root / "reports").mkdir()
    (fake_root / "reports" / "error_analysis.md").write_text("synthetic", encoding="utf-8")
    assert dq.present_denied_files(fake_root) == ["data/raw/heart.csv", "reports/error_analysis.md"]
    (fake_root / "data" / "raw" / "heart.csv").unlink()
    (fake_root / "reports" / "error_analysis.md").unlink()
    assert dq.present_denied_files(fake_root) == []


def test_sparse_patterns_cover_every_denied_file():
    patterns = dq.sparse_checkout_patterns()
    assert patterns[:2] == ["/*", "!/data/*"]
    assert all(f"!/{p}" in patterns for p in dq.LOCKED_DERIVED)
    assert all(f"/{p}" in patterns for p in dq.ALLOWED_DATA_DOCS)


# --- Static guard ---------------------------------------------------------------------------

def test_static_references_ignore_docstrings_and_find_code_literals():
    tokens = sg.protected_tokens()
    src = '"""Mentions heart.csv in a docstring only."""\n\ndef f():\n    """Also heart.csv here."""\n    return 1\n'
    assert sg.references(src, tokens) == []
    assert sg.references('P = "data/raw/heart.csv"\n', tokens) == ["heart.csv"]
    assert sg.references('from x import load_locked_test\n', tokens) == ["load_locked_test"]
    assert sg.references('x = obj.load_locked_test(df)\n', tokens) == ["load_locked_test"]
    assert "dev_indices.json" in sg.references('p = root / "data" / "processed" / "dev_indices.json"\n', tokens)


def test_static_check_flags_unregistered_stale_and_unsafe_tests():
    found = {"src/new_loader.py": ["heart.csv"], "tests/test_x.py": ["heart.csv"]}
    registry = {"tests/test_x.py": {"role": "research_data_access", "reason": "r"}, "gone.py": {"role": "path_reference", "reason": "r"}}
    problems = sg.check(found, registry, {"tests/test_x.py"})
    assert any(p.startswith("UNAUTHORIZED: src/new_loader.py") for p in problems)
    assert any(p.startswith("STALE: gone.py") for p in problems)
    assert any(p.startswith("UNSAFE CI TEST: tests/test_x.py") for p in problems)


def test_repository_passes_static_guard():
    problems = sg.check(sg.scan(), sg.load_registry(), set(tc.ci_safe()))
    assert problems == [], problems


# --- Test classification and workflow ---------------------------------------------------------

def test_every_test_module_is_classified_once():
    assert tc.check() == []
    assert set(tc.ci_safe()).isdisjoint(tc.research_data())
    assert "tests/test_data_quarantine.py" in tc.ci_safe()


def _jobs(wf: str) -> dict:
    """Top-level job blocks of the workflow (two-space-indented keys under `jobs:`)."""
    body = wf.split("\njobs:\n", 1)[1]
    parts = re.split(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", body)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def test_workflow_runs_only_classified_safe_tests_under_quarantine():
    wf = WORKFLOW.read_text(encoding="utf-8")
    jobs = _jobs(wf)
    assert set(jobs) == {"verify-backend", "quarantined-research-tests", "verify-frontend", "deploy", "verify-production"}
    assert not re.search(r"pytest\s+(tests/?|backend/tests/?)(\s|$)", wf), "broad test-directory execution must not return"
    assert "--ignore=tests/" not in wf
    assert dq.check_sparse_checkout(wf) == []
    for job in ("verify-backend", "quarantined-research-tests"):
        block = jobs[job]
        assert "sparse-checkout-cone-mode: false" in block and "CARDIOVANTA_DATA_QUARANTINE=1" in block
        assert "scripts/ci/check_data_access.py" in block and "test_classification.py --check" in block
        assert "--assert-absent" in block and "--assert-clean-log" in block and "if: always()" in block
        pytest_lines = [l for l in block.splitlines() if "pytest" in l and "pip install" not in l and not l.strip().startswith("#")]
        assert pytest_lines and all("test_classification.py --list ci_safe" in l for l in pytest_lines)
        # the guard is enabled before any test or verification step runs
        assert block.index("Enable Data Quarantine Guard") < block.index("Verify Quarantine") < block.index("pytest $(")
        # bytecode caches are never written, so imports from write-protected package directories
        # (cardiovanta_ml/contracts) do not produce refused __pycache__ writes (PR #2 CI finding)
        assert 'echo "PYTHONDONTWRITEBYTECODE=1" >> "$GITHUB_ENV"' in block
        assert block.index("PYTHONDONTWRITEBYTECODE=1") < block.index("Verify Quarantine")
    # the protected-directory policy is not weakened to accommodate caches
    assert "cardiovanta_ml/contracts" in dq.WRITE_PROTECTED_DIRS
    assert dq.decide("open", (str(ROOT / "cardiovanta_ml" / "contracts" / "__pycache__" / "x.pyc.1"), "wb", 0))["reason"] == "write_protected"
    assert "sparse-checkout-cone-mode: false" in jobs["verify-frontend"]
    # every job that checks out the repository, including deploy and verify-production, uses the
    # quarantine sparse checkout, so protected files are never present on any runner
    for job, block in jobs.items():
        if "actions/checkout@" in block:
            assert "sparse-checkout-cone-mode: false" in block, job
            assert all(p in block for p in dq.sparse_checkout_patterns()), job
    deploy_needs = re.search(r"needs: \[([^\]]*)\]", jobs["deploy"]).group(1)
    assert "research-data-tests" not in deploy_needs and "quarantined-research-tests" in deploy_needs


_FEATURE = r"(?:age|sex|cp|trestbps|chol|fbs|restecg|thalach|exang|oldpeak|slope|ca|thal|target)"
_KV = re.compile(rf"\b{_FEATURE}\s*[=:]\s*-?\d")
_CSV_ROW = re.compile(r"^\s*`?\s*-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?){12,13}\s*`?\s*$")


def _patient_rows(text: str):
    """Line numbers that look like an individual observation (>= 8 feature=value pairs, or a 13-14 value CSV row)."""
    return [n for n, l in enumerate(text.splitlines(), 1) if len(_KV.findall(l)) >= 8 or _CSV_ROW.match(l)]


def test_patient_row_detector():
    # Deliberately impossible placeholder values, so no test string can coincide with a real observation.
    assert _patient_rows("`age=999, sex=9, cp=9, trestbps=999, chol=999, fbs=9, restecg=9, thalach=999, exang=9`") == [1]
    assert _patient_rows("x\n999,9,9,999,999,9,9,999,9,9.9,9,9,9,9") == [2]
    assert _patient_rows("initialData: age 54, sex 1, cp 0 (synthetic form defaults)") == []
    assert _patient_rows("AUC 0.91, Brier 0.12, slope 1.29") == []


def test_readable_reports_and_docs_contain_no_patient_rows():
    files = {p for pat in ("reports/**/*.md", "docs/**/*.md", "*.md", "openspec/**/*.md") for p in ROOT.glob(pat)}
    scanned = 0
    for p in sorted(files):
        rel = p.relative_to(ROOT).as_posix()
        if dq.read_denial(rel.lower() if os.name == "nt" else rel):
            continue                                    # quarantined files are never opened by tests
        assert _patient_rows(p.read_text(encoding="utf-8", errors="replace")) == [], rel
        scanned += 1
    assert scanned > 50


@pytest.mark.skipif(os.environ.get("CARDIOVANTA_DATA_QUARANTINE") == "1"
                    or not (ROOT / "reports" / "cardio_vanta_master_audit.md").exists(),
                    reason="quarantined in CI (absent from the sparse checkout)")
def test_master_audit_report_raw_row_is_redacted():
    text = (ROOT / "reports" / "cardio_vanta_master_audit.md").read_text(encoding="utf-8")
    assert _patient_rows(text) == []
    assert "Redacted 2026-11-01" in text and not re.search(r"row index \d+", text)
    assert "dev_groups" in text and "StratifiedGroupKFold" in text     # the useful finding is preserved


def test_research_data_modules_are_not_executed_by_ci():
    wf = WORKFLOW.read_text(encoding="utf-8")
    for path in tc.research_data():
        assert path not in wf, path
