"""
Static guard: detect unauthorized direct references to quarantined research data.

Every Python file (outside virtual environments, node_modules and caches) is parsed with ``ast``.
A file *references* quarantined data if a non-docstring string literal names a protected
resource (see ``scripts/ci/data_quarantine.py``: the locked source, locked-derived outputs,
research-data files) or it uses a known locked-partition accessor (``load_locked_test``).

Each referencing file must appear in ``scripts/ci/data_access_registry.json`` with a role:

  research_data_access   code that reads research data (must never run in default CI)
  negative_assertion     tests that name protected paths only to assert they are NOT used
  path_reference         configuration, provenance or exclusion lists that never open the data

An unregistered reference fails the check, and so does a stale registry entry (file gone or no
longer referencing data). Default-CI test modules (``ci_safe`` in ``scripts/ci/test_classification.py``)
may hold only ``negative_assertion`` or ``path_reference`` roles.

Run:  python scripts/ci/check_data_access.py [--report]
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from pathlib import Path
from typing import Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "scripts" / "ci" / "data_access_registry.json"
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", ".next", "build", "dist", ".pytest_cache",
             ".mypy_cache", "site-packages", ".vercel"}
ROLES = {"research_data_access", "negative_assertion", "path_reference"}
SAFE_TEST_ROLES = {"negative_assertion", "path_reference"}
ACCESSOR_NAMES = {"load_locked_test"}


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dq = _load("cardiovanta_data_quarantine_static", "scripts/ci/data_quarantine.py")


def protected_tokens() -> Set[str]:
    """Basenames of every protected resource, plus research-data file names under data/."""
    names = {Path(p).name for p in dq.LOCKED_SOURCES + dq.LOCKED_DERIVED}
    names |= {"dev_indices.json", "hungarian.data", "long-beach-va.data", "switzerland.data",
              "processed.cleveland.data", "cleveland.data"}
    return names


def _docstring_nodes(tree: ast.AST) -> Set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def references(source: str, tokens: Set[str]) -> List[str]:
    """Sorted protected tokens / accessors referenced by non-docstring code in ``source``."""
    tree = ast.parse(source)
    skip = _docstring_nodes(tree)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            for t in tokens:
                if t in node.value:
                    found.add(t)
        elif isinstance(node, ast.Name) and node.id in ACCESSOR_NAMES:
            found.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in ACCESSOR_NAMES:
            found.add(node.attr)
        elif isinstance(node, (ast.ImportFrom,)):
            for a in node.names:
                if a.name in ACCESSOR_NAMES:
                    found.add(a.name)
    return sorted(found)


def python_files(root: Path = REPO_ROOT) -> List[Path]:
    out = []
    for p in root.rglob("*.py"):
        rel_parts = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        out.append(p)
    return sorted(out)


def scan(root: Path = REPO_ROOT) -> Dict[str, List[str]]:
    tokens = protected_tokens()
    result = {}
    for p in python_files(root):
        try:
            refs = references(p.read_text(encoding="utf-8", errors="replace"), tokens)
        except SyntaxError as exc:
            refs = [f"<syntax error: {exc.msg}>"]
        if refs:
            result[p.relative_to(root).as_posix()] = refs
    return result


def check(found: Dict[str, List[str]], registry: Dict[str, Dict], ci_safe_tests: Set[str]) -> List[str]:
    problems = []
    for path, refs in sorted(found.items()):
        entry = registry.get(path)
        if entry is None:
            problems.append(f"UNAUTHORIZED: {path} references quarantined data {refs} but is not registered")
        elif entry.get("role") not in ROLES:
            problems.append(f"INVALID ROLE: {path} has role {entry.get('role')!r}")
        elif not entry.get("reason"):
            problems.append(f"MISSING REASON: {path}")
    for path in sorted(set(registry) - set(found)):
        problems.append(f"STALE: {path} is registered but no longer references quarantined data")
    for path in sorted(ci_safe_tests):
        role = registry.get(path, {}).get("role")
        if role is not None and role not in SAFE_TEST_ROLES:
            problems.append(f"UNSAFE CI TEST: {path} has role {role!r} but is classified ci_safe")
    return problems


def load_registry() -> Dict[str, Dict]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["files"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print references without checking the registry")
    args = ap.parse_args(argv)
    found = scan()
    if args.report:
        print(json.dumps(found, indent=2))
        return 0
    tc = _load("cardiovanta_test_classification", "scripts/ci/test_classification.py")
    problems = check(found, load_registry(), set(tc.ci_safe()))
    for p in problems:
        print(f"::error::{p}")
    print(f"Static data-access guard: {len(found)} referencing file(s) checked, {len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
