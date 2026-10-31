#!/usr/bin/env python3
"""
Inspect the Python function produced by `vercel build` (R3.1). Synthetic inputs only.

    python scripts/ci/inspect_vercel_bundle.py --output .vercel/output --build-log vercel-build.log \
        --report bundle-report.json

Reports, and exits 1 if any required check fails:
  * Python version and dependency source detected by the builder (from the build log).
  * The function directory, its .vc-config.json (runtime/handler) and total uncompressed size.
  * A size breakdown: top-level entries and the largest vendored packages.
  * Whether dependencies were externalized to runtime installation (/tmp/_vc_deps) or bundled.
  * Presence of the registry entry, the six model artifacts, the canonical contract and the
    cardiovanta_ml package resources inside the function.
  * That cardiovanta-lr13@1.0.0 loads from the bundle's own registry root with golden
    probabilities, and that an unregistered version is rejected (no fallback).

Never reads .vercel/.env* files (they contain pulled environment variables).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ENTRY = "artifacts/models/cardiovanta-lr13/1.0.0"
REQUIRED = [
    f"{ENTRY}/metadata.json", f"{ENTRY}/checksums.sha256", f"{ENTRY}/model_card.md",
    "artifacts/model/model.joblib", "artifacts/model/explanation_model.joblib", "artifacts/model/metadata.json",
    "artifacts/model/feature_schema.json", "artifacts/model/shap_background.json",
    "artifacts/model/reference_predictions.csv",
    "cardiovanta_ml/contracts/feature_schema.v2.json", "cardiovanta_ml/contracts/generated_features.py",
    "cardiovanta_ml/registry/loader.py", "cardiovanta_ml/registry/integrity.py", "cardiovanta_ml/inference/predict.py",
    "api/index.py", "backend/app/main.py",
]
MB = 1024 * 1024


def dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            p = Path(root) / f
            if not p.is_symlink():
                total += p.stat().st_size
    return total


def find_function(output: Path) -> Path:
    candidates = [p.parent for p in (output / "functions").rglob(".vc-config.json")
                  if json.loads(p.read_text()).get("runtime", "").startswith("python")]
    if len(candidates) != 1:
        raise SystemExit(f"Expected exactly one Python function in {output}/functions, found {candidates}")
    return candidates[0]


def find_project_root(func: Path) -> Path:
    hits = list(func.rglob(f"{ENTRY}/metadata.json"))
    if len(hits) != 1:
        raise SystemExit(f"Registry entry {ENTRY} found {len(hits)} times in the function bundle")
    return hits[0].parents[4]  # .../<root>/artifacts/models/cardiovanta-lr13/1.0.0/metadata.json


def probe(root: Path, func: Path, version: str) -> dict:
    """Load the model from the bundle's own registry root in a separate interpreter."""
    vendor_dirs = [str(p) for p in func.rglob("site-packages") if p.is_dir()]
    code = (
        "import sys, json, os\n"
        f"sys.path[:0] = [{str(root)!r}] + {vendor_dirs!r}\n"
        "os.environ['MODEL_VERSION'] = sys.argv[1]\n"
        "from fastapi.testclient import TestClient\n"
        "from api.index import app\n"
        "hi = dict(age=67.0,sex=1,cp=0,trestbps=160.0,chol=286.0,fbs=0,restecg=0,thalach=108.0,exang=1,oldpeak=3.0,slope=1,ca=3,thal=3)\n"
        "lo = dict(age=37.0,sex=0,cp=2,trestbps=120.0,chol=200.0,fbs=0,restecg=1,thalach=187.0,exang=0,oldpeak=0.0,slope=2,ca=0,thal=2)\n"
        "with TestClient(app) as c:\n"
        "    e = app.state.inference_engine.loaded\n"
        "    print('PROBE ' + json.dumps({'model': e.metadata.qualified_name, 'root': str(e.artifact_dir.parent),\n"
        "        'p_high': c.post('/api/v1/predict', json=hi).json()['prediction']['probability'],\n"
        "        'p_low': c.post('/api/v1/predict', json=lo).json()['prediction']['probability']}))\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "MODEL_ID", "MODEL_REGISTRY_ROOT")}
    r = subprocess.run([sys.executable, "-c", code, version], cwd=root, env=env, capture_output=True, text=True, timeout=600)
    lines = [l[6:] for l in r.stdout.splitlines() if l.startswith("PROBE ")]
    return {"returncode": r.returncode, "result": json.loads(lines[0]) if lines else None, "stderr_tail": r.stderr[-1500:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path(".vercel/output"))
    ap.add_argument("--build-log", type=Path, required=True)
    ap.add_argument("--report", type=Path, default=Path("bundle-report.json"))
    args = ap.parse_args()

    failures, report = [], {}

    def check(name, ok, detail=None):
        report.setdefault("checks", {})[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    log = args.build_log.read_text(encoding="utf-8", errors="replace") if args.build_log.exists() else ""
    py_line = next((l for l in log.splitlines() if "Python" in l and ("Using Python" in l or "python version" in l)), None)
    dep_line = next((l for l in log.splitlines() if "Installing required dependencies" in l), None)
    check("python_3_12_from_api_python_version", py_line is not None and "3.12" in py_line and "api" in py_line, py_line)
    check("dependencies_from_api_requirements", dep_line is not None and ("api" in dep_line or "uv.lock" in dep_line), dep_line)
    report["builder_size_messages"] = [l for l in log.splitlines() if re.search(r"bundle size|Force-bundling|externaliz|runtime dependency|exceeds", l, re.I)]

    func = find_function(args.output)
    vc = json.loads((func / ".vc-config.json").read_text())
    report["function"] = {"path": str(func), "runtime": vc.get("runtime"), "handler": vc.get("handler"),
                          "vc_config_keys": sorted(vc)}
    total = dir_size(func)
    report["total_uncompressed_mb"] = round(total / MB, 2)
    report["top_level_mb"] = dict(sorted(((p.name, round(dir_size(p) / MB if p.is_dir() else p.stat().st_size / MB, 2))
                                          for p in func.iterdir()), key=lambda kv: -kv[1]))
    packages = {}
    for sp in func.rglob("site-packages"):
        for p in sp.iterdir():
            packages[p.name] = packages.get(p.name, 0) + (dir_size(p) if p.is_dir() else p.stat().st_size)
    report["largest_vendored_packages_mb"] = dict(sorted(((k, round(v / MB, 2)) for k, v in packages.items()),
                                                         key=lambda kv: -kv[1])[:20])
    report["runtime_install_mode"] = bool(re.search(r"_vc_deps|runtime dependency installation", log)) or \
        any("_vc_deps" in str(p) for p in func.rglob("*uv.lock"))
    check("within_python_bundle_limit_500mb", total <= 500 * MB, report["total_uncompressed_mb"])

    root = find_project_root(func)
    missing = [rel for rel in REQUIRED if not (root / rel).is_file()]
    check("required_resources_present", not missing, missing or f"{len(REQUIRED)} files under {root}")
    report["included_project_mb"] = {top: round(dir_size(root / top) / MB, 3)
                                     for top in ("artifacts", "cardiovanta_ml", "backend", "src", "configs", "api")
                                     if (root / top).exists()}

    ok_probe = probe(root, func, "1.0.0")
    res = ok_probe["result"] or {}
    check("loads_cardiovanta_lr13_1_0_0", ok_probe["returncode"] == 0 and res.get("model") == "cardiovanta-lr13@1.0.0",
          res or ok_probe["stderr_tail"])
    check("registry_root_inside_bundle", str(res.get("root", "")).startswith(str(root)), res.get("root"))
    check("golden_probabilities", abs(res.get("p_high", 0) - 0.985790929) < 1e-6 and abs(res.get("p_low", 1) - 0.016065906) < 1e-6,
          {k: res.get(k) for k in ("p_high", "p_low")})
    bad_probe = probe(root, func, "9.9.9")
    check("no_fallback_for_unregistered_version",
          bad_probe["returncode"] != 0 and bad_probe["result"] is None and "not registered" in bad_probe["stderr_tail"],
          bad_probe["stderr_tail"][-300:])

    report["failures"] = failures
    args.report.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
