"""
CardioVanta research-data quarantine: shared policy and runtime guard.

Purpose
-------
Default CI jobs (and any local run that opts in) must never open, parse or load the 61 locked
Cleveland observations. In this repository the locked rows exist only inside
``data/raw/heart.csv`` (no locked-index file exists; the locked partition is the complement of
``data/processed/dev_indices.json``). Several historical research outputs were also computed on
the locked partition and are treated as locked-derived.

The policy has three categories:

* LOCKED_SOURCES   files that contain the locked observations themselves;
* LOCKED_DERIVED   research outputs whose producers evaluated or analysed the locked partition
                   (classified from their producing code, never by opening them);
* RESEARCH_DATA    every other file under ``data/`` (development indices, external cohorts),
                   except allow-listed documentation such as the UCI codebook text.

All three are denied for reading. In addition, research results, production artifacts, the
clinical contract and data are WRITE_PROTECTED (no write, delete or rename).

Runtime enforcement
-------------------
``install()`` registers a ``sys.addaudithook`` hook (it cannot be removed) that raises
``PermissionError`` on any ``open`` of a denied path and on writes/deletes/renames inside
write-protected directories. Every refused attempt is appended to a JSON-lines log
(``CARDIOVANTA_QUARANTINE_LOG``) so that attempts swallowed by a test are still detected by
``--assert-clean-log``. Activation is via ``scripts/ci/quarantine_site/sitecustomize.py`` when
``CARDIOVANTA_DATA_QUARANTINE=1`` and that directory is on ``PYTHONPATH``, so Python subprocesses
inherit the guard (except interpreters started with ``-I``/``-E``).

Deletes, renames and chmods made relative to a directory descriptor (``dir_fd``, as
``shutil.rmtree`` does on Linux) are resolved against the directory that descriptor refers to.

Limitations: audit hooks see Python-level opens (``open``, ``io.open``, ``os.open``, pandas,
NumPy, joblib); they do not see opens made directly by C libraries or non-Python processes. The
``open`` audit event carries no ``dir_fd``, so a ``dir_fd``-relative ``os.open`` is resolved against
the current directory.
CI therefore also excludes every denied file from the checkout (sparse checkout), so such files
are not present on the runner at all.

CLI
---
  python scripts/ci/data_quarantine.py --assert-clean-log LOG   fail if any attempt was logged
  python scripts/ci/data_quarantine.py --sparse-checkout          print the CI sparse-checkout patterns
  python scripts/ci/data_quarantine.py --check-sparse-checkout WORKFLOW
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FLAG = "CARDIOVANTA_DATA_QUARANTINE"
ENV_LOG = "CARDIOVANTA_QUARANTINE_LOG"

LOCKED_SOURCES = (
    "data/raw/heart.csv",
)
# Classified from the producing code (src/experiment/final_evaluation.py, experiments/formal_error_analysis.py,
# experiments/advanced_model_search.py, experiments/nested_*.py, experiments/next_research_phase_90pct.py,
# src/experiment/phase13/*, src/experiment/baseline.py); none of these files was opened to classify it.
LOCKED_DERIVED = (
    "experiments/results/error_analysis.json",
    "experiments/results/candidate_comparison.json",
    "experiments/results/nested_lda_evaluation.json",
    "experiments/results/nested_threshold_optimization.json",
    "experiments/results/nested_cv_90pct_results.json",
    "experiments/phase13/test_results.json",
    "experiments/phase13/tabicl_test_results.json",
    "reports/error_analysis.md",
    "reports/phase2c_final_evaluation.csv",
    "reports/phase2c_final_evaluation.json",
    "reports/phase2c_model_selection.json",
    "reports/model_baseline_results.csv",
    "reports/model_baseline_results.json",
    "reports/cardio_vanta_master_audit.md",      # embeds a raw heart.csv row (R6 hygiene finding)
)
RESEARCH_DATA_GLOBS = ("data/*",)                 # fnmatch '*' also matches '/', so this covers data/**
ALLOWED_DATA_DOCS = (
    "data/external/raw/heart-disease.names",      # UCI codebook text (documentation, no observations)
)
WRITE_PROTECTED_DIRS = (
    "artifacts", "data", "experiments/results", "experiments/phase13", "reports", "cardiovanta_ml/contracts",
)

_state = threading.local()
_installed = False


ENV_EXTRA_ROOTS = "CARDIOVANTA_QUARANTINE_EXTRA_ROOTS"   # other checkouts to protect (os.pathsep-separated)


def _roots() -> List[Path]:
    extra = [Path(r) for r in os.environ.get(ENV_EXTRA_ROOTS, "").split(os.pathsep) if r.strip()]
    return [REPO_ROOT] + extra


def _rel(path) -> Optional[str]:
    """Path relative to the repository (or an extra protected root), POSIX style; None if outside or not a path."""
    if isinstance(path, int):
        return None
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    try:
        p = Path(os.fspath(path))
    except TypeError:
        return None
    absolute = os.path.abspath(p if p.is_absolute() else Path.cwd() / p)
    for root in _roots():
        try:
            rel = os.path.relpath(absolute, os.path.abspath(root))
        except ValueError:                    # different drive on Windows
            continue
        if not rel.startswith(".."):
            rel = rel.replace(os.sep, "/")
            return rel.lower() if os.name == "nt" else rel
    return None


def _norm(entries) -> List[str]:
    return [e.lower() if os.name == "nt" else e for e in entries]


def read_denial(rel: Optional[str]) -> Optional[str]:
    """Reason a read of ``rel`` is denied, or None if allowed."""
    if rel is None:
        return None
    if rel in _norm(ALLOWED_DATA_DOCS):
        return None
    if rel in _norm(LOCKED_SOURCES):
        return "locked_source"
    if rel in _norm(LOCKED_DERIVED):
        return "locked_derived"
    if any(fnmatch.fnmatch(rel, g) for g in _norm(RESEARCH_DATA_GLOBS)):
        return "research_data"
    return None


def write_denial(rel: Optional[str]) -> Optional[str]:
    if rel is None:
        return None
    for d in _norm(WRITE_PROTECTED_DIRS):
        if rel == d or rel.startswith(d + "/"):
            return "write_protected"
    return None


def _is_write_mode(mode, flags) -> bool:
    if isinstance(mode, str) and any(c in mode for c in "wax+"):
        return True
    if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        return True
    return False


def _fd_dir(dir_fd) -> Optional[str]:
    """Directory that an open directory descriptor refers to, or None if there is none or it is unknown.

    CPython reports "no dir_fd" as -1 (os.*) or None (shutil.rmtree)."""
    if not isinstance(dir_fd, int) or isinstance(dir_fd, bool) or dir_fd < 0:
        return None
    try:
        return os.readlink(f"/proc/self/fd/{dir_fd}")          # Linux
    except OSError:
        pass
    try:                                                       # macOS
        import fcntl
        if hasattr(fcntl, "F_GETPATH"):
            return os.fsdecode(fcntl.fcntl(dir_fd, fcntl.F_GETPATH, bytes(1024)).split(b"\0", 1)[0])
    except (ImportError, OSError, ValueError):
        pass
    return None


def _at(path, dir_fd):
    """The location a (path, dir_fd) pair really names.

    A relative path with a dir_fd is relative to that directory, not to the CWD. shutil.rmtree on Linux
    deletes with os.rmdir(name, dir_fd=parent_fd), so resolving such names against the CWD both refuses
    unrelated deletions (e.g. a temporary venv's ``.../tests/data``) and lets deletions inside a protected
    directory through. If the descriptor cannot be resolved, the path is left as is (CWD-relative, the
    previous behaviour), so an unknown descriptor never relaxes the policy."""
    if isinstance(path, int):
        return path
    base = _fd_dir(dir_fd)
    if base is None:
        return path
    try:
        p = os.fsdecode(os.fspath(path))
    except TypeError:
        return path
    return p if os.path.isabs(p) else os.path.join(base, p)


# Position of the dir_fd argument in each audit event's arguments (CPython 3.11+).
_DIR_FD_ARG = {"os.remove": 1, "os.rmdir": 1, "shutil.rmtree": 1, "os.chmod": 2}


def decide(event: str, args) -> Optional[Dict]:
    """Pure policy decision for an audit event; returns a denial record or None."""
    if event == "open":
        # The "open" audit event carries no dir_fd (CPython limitation), so a dir_fd-relative os.open is
        # resolved against the CWD; the sparse checkout keeps denied files off CI runners regardless.
        path, mode, flags = (list(args) + [None, None, None])[:3]
        rel = _rel(path)
        reason = read_denial(rel) or (write_denial(rel) if _is_write_mode(mode, flags) else None)
        return {"event": event, "path": rel, "reason": reason} if reason else None
    if event in ("os.remove", "os.rmdir", "os.truncate", "shutil.rmtree", "os.chmod"):
        pos = _DIR_FD_ARG.get(event)
        dir_fd = args[pos] if pos is not None and len(args) > pos else None
        rel = _rel(_at(args[0], dir_fd)) if args else None
        reason = read_denial(rel) or write_denial(rel)
        return {"event": event, "path": rel, "reason": reason} if reason else None
    if event in ("os.rename", "shutil.move", "shutil.copyfile", "os.link", "os.symlink"):
        a = list(args) + [None, None, None, None]
        src, dst = a[0], a[1]
        if event in ("os.rename", "os.link"):                  # (src, dst, src_dir_fd, dst_dir_fd)
            src, dst = _at(src, a[2]), _at(dst, a[3])
        elif event == "os.symlink":                            # (src, dst, dir_fd): only dst is dir_fd-relative
            dst = _at(dst, a[2])
        rs, rd = _rel(src), _rel(dst)
        reason = read_denial(rs) or write_denial(rd) or (write_denial(rs) if event in ("os.rename", "shutil.move") else None)
        return {"event": event, "path": rs if read_denial(rs) else rd, "reason": reason} if reason else None
    return None


def _log(record: Dict) -> None:
    log = os.environ.get(ENV_LOG)
    if not log:
        return
    with open(log, "a", encoding="utf-8") as fh:   # log lives outside the repository (runner temp)
        fh.write(json.dumps({**record, "pid": os.getpid()}) + "\n")


def _hook(event: str, args) -> None:
    if getattr(_state, "active", False):
        return
    if event not in ("open", "os.remove", "os.rmdir", "os.truncate", "shutil.rmtree", "os.chmod",
                     "os.rename", "shutil.move", "shutil.copyfile", "os.link", "os.symlink"):
        return
    _state.active = True
    try:
        record = decide(event, args)
        if record:
            _log(record)
    finally:
        _state.active = False
    if record:
        raise PermissionError(f"CardioVanta data quarantine: {record['reason']} access refused for "
                              f"{record['path']!r} ({event}). See scripts/ci/data_quarantine.py.")


def install() -> bool:
    """Install the irreversible audit hook once per interpreter. Returns True if newly installed."""
    global _installed
    if _installed:
        return False
    sys.addaudithook(_hook)
    _installed = True
    return True


def sparse_checkout_patterns() -> List[str]:
    """Non-cone sparse-checkout patterns that keep every denied file off the CI runner."""
    lines = ["/*", "!/data/*"]
    lines += [f"/{d}" for d in ALLOWED_DATA_DOCS]
    lines += [f"!/{p}" for p in LOCKED_DERIVED]
    return lines


def check_sparse_checkout(workflow_text: str) -> List[str]:
    """Return problems if any checkout in the workflow's quarantined jobs lacks the required patterns."""
    problems = []
    for pattern in sparse_checkout_patterns():
        if pattern not in workflow_text:
            problems.append(f"missing sparse-checkout pattern {pattern!r}")
    return problems


def present_denied_files(root: Path = REPO_ROOT) -> List[str]:
    """Denied files that exist in a checkout (checked by name with os.path.lexists; nothing is opened)."""
    present = [p for p in LOCKED_SOURCES + LOCKED_DERIVED if os.path.lexists(root / p)]
    data = root / "data"
    if data.is_dir():
        allowed = set(_norm(ALLOWED_DATA_DOCS))
        for dirpath, _dirs, files in os.walk(data):
            for f in files:
                rel = (Path(dirpath) / f).relative_to(root).as_posix()
                if (rel.lower() if os.name == "nt" else rel) not in allowed:
                    present.append(rel)
    return sorted(set(present))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--assert-clean-log", type=Path)
    g.add_argument("--sparse-checkout", action="store_true")
    g.add_argument("--check-sparse-checkout", type=Path)
    g.add_argument("--assert-absent", action="store_true", help="fail if any denied file exists in this checkout")
    args = ap.parse_args(argv)
    if args.assert_absent:
        present = present_denied_files()
        for p in present:
            print(f"::error::Quarantined file present in checkout: {p}")
        print(f"Quarantined files present: {len(present)}.")
        return 1 if present else 0
    if args.sparse_checkout:
        print("\n".join(sparse_checkout_patterns()))
        return 0
    if args.check_sparse_checkout:
        problems = check_sparse_checkout(args.check_sparse_checkout.read_text(encoding="utf-8"))
        for p in problems:
            print(f"::error::{p}")
        return 1 if problems else 0
    log = args.assert_clean_log
    records = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()] if log.exists() else []
    for r in records:
        print(f"::error::Quarantine refused {r['reason']} access to {r['path']} ({r['event']}, pid {r['pid']})")
    print(f"Data quarantine log: {len(records)} refused attempt(s).")
    return 1 if records else 0


if __name__ == "__main__":
    sys.exit(main())
