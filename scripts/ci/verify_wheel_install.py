#!/usr/bin/env python3
"""
Verify an INSTALLED cardiovanta_ml wheel (R3). Run it with the interpreter of a clean
virtual environment, from a working directory outside the repository:

    <venv python> scripts/ci/verify_wheel_install.py --registry-root <abs path to artifacts> \
        --model-id cardiovanta-lr13 --model-version 1.0.0 --repo-root <abs repo path>

The script runs in isolated mode (-I semantics enforced below), so the script directory
and current directory are not on sys.path, and only the installed package is importable.

Checks (exit code 1 on any failure):
  1. cardiovanta_ml is imported from site-packages, not from the repository.
  2. The contract resource loads via importlib.resources. Its canonical SHA-256 equals the
     generated module's, and both equal the registry metadata's feature_contract.
  3. The exact registered model loads through the registry (all integrity checks run before
     deserialization). The artifact manifest is re-verified independently and must match.
  4. Synthetic golden predictions, threshold classes and explanation directions hold.
  5. FastAPI / Starlette are never imported, and are blocked outright.
  6. Resource access does not depend on the working directory (re-checked after chdir).
Uses only synthetic inputs; no dataset is read.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

for blocked in ("fastapi", "starlette", "backend", "src"):
    sys.modules[blocked] = None  # any import attempt raises ImportError

HIGH = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
            thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)
LOW = dict(age=37.0, sex=0, cp=2, trestbps=120.0, chol=200.0, fbs=0, restecg=1,
           thalach=187.0, exang=0, oldpeak=0.0, slope=2, ca=0, thal=2)
GOLDEN = {"high": 0.985790929, "low": 0.016065906}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry-root", required=True, type=Path)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--model-version", required=True)
    ap.add_argument("--repo-root", required=True, type=Path)
    args = ap.parse_args()

    if not sys.flags.isolated:
        print("FAIL: run with python -I (isolated mode)")
        return 1
    failures, report = [], {}

    def check(name, ok, detail=""):
        report[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    import cardiovanta_ml
    from cardiovanta_ml import InferenceEngine, load_model
    from cardiovanta_ml.contracts import bundled_contract_sha256, load_contract
    from cardiovanta_ml.contracts import generated_features as g
    from cardiovanta_ml.registry.integrity import verify_artifacts, verify_manifest_file
    from cardiovanta_ml.registry.metadata import declared_files

    pkg_file = Path(cardiovanta_ml.__file__).resolve()
    check("installed_copy_not_repo", args.repo_root.resolve() not in pkg_file.parents, str(pkg_file))
    check("python_version", sys.version_info[:2] in ((3, 11), (3, 12)), sys.version.split()[0])

    m = load_model(args.model_id, args.model_version, registry_root=args.registry_root.resolve())
    meta = m.metadata
    check("exact_model_selected", (m.model_id, m.model_version) == (args.model_id, args.model_version),
          meta.qualified_name)
    check("contract_hash_consistent",
          bundled_contract_sha256() == g.CONTRACT_SHA256 == meta.feature_contract.sha256,
          f"bundled={bundled_contract_sha256()[:12]} generated={g.CONTRACT_SHA256[:12]} registry={meta.feature_contract.sha256[:12]}")
    check("contract_version_consistent",
          load_contract()["contract_version"] == g.CONTRACT_VERSION == meta.feature_contract.version,
          g.CONTRACT_VERSION)

    manifest = verify_manifest_file(m.entry_dir / meta.checksum_manifest, meta.checksum_manifest_sha256)
    verified = verify_artifacts(m.artifact_dir, manifest, declared_files(meta))
    check("integrity_reverified", sorted(verified) == sorted(meta.artifacts.values()), f"{len(verified)} artifacts")
    check("disease_label_mapping", m.disease_label == 0 and meta.class_label_semantics == {0: "disease_present", 1: "disease_absent"},
          str(meta.class_label_semantics))

    engine = InferenceEngine(m)
    ph, pl = engine.predict(HIGH, 0.5), engine.predict(LOW, 0.5)
    check("golden_high", abs(ph["probability"] - GOLDEN["high"]) < 1e-6, f"{ph['probability']:.6f}")
    check("golden_low", abs(pl["probability"] - GOLDEN["low"]) < 1e-6, f"{pl['probability']:.6f}")
    check("threshold_classes", (ph["class"], pl["class"]) == (1, 0), f"{ph['class']},{pl['class']}")
    lin, shap = engine.explain(HIGH), engine.explain_shap_equivalent(HIGH)
    check("explanation_direction",
          all(e["contributions"][f] > 0 for e in (lin, shap) for f in ("exang", "oldpeak", "ca"))
          and lin["decision_function_log_odds"] > 0 and engine.explain(LOW)["decision_function_log_odds"] < 0)
    check("explanation_additivity",
          abs(lin["intercept"] + sum(lin["contributions"].values()) - lin["decision_function_log_odds"]) < 1e-6)

    check("no_fastapi_imported", not any(k in sys.modules and sys.modules[k] is not None
                                         for k in ("fastapi", "starlette", "uvicorn")))
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as other:
        os.chdir(other)
        try:
            check("cwd_independent_resources", bundled_contract_sha256() == g.CONTRACT_SHA256, other)
        finally:
            os.chdir(original_cwd)  # Windows cannot delete the current directory

    report["summary"] = {"failures": failures, "python": sys.version.split()[0], "package": cardiovanta_ml.__version__}
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
