"""
Register a portable (NumPy-only) copy of a joblib-registered CardioVanta model.

    python scripts/research/export_portable_model.py --source-version 1.1.0 --target-version 1.1.1

Reads the integrity-verified source model through the registry (needs scikit-learn), exports its fitted
parameters with cardiovanta_ml.inference.portable, verifies on 50,000 random inputs that the portable model
reproduces the source probabilities and explanation log-odds, and writes:

  artifacts/model-<target>/                 model.json, explanation_model.json, feature_schema.json,
                                            shap_background.json, reference_predictions.csv, metadata.json
  artifacts/models/cardiovanta-lr13/<target>/  metadata.json, checksums.sha256, model_card.md

The model card is written separately. The contract's model_label_mappings must list the target version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cardiovanta_ml import load_model  # noqa: E402
from cardiovanta_ml.inference import portable as P  # noqa: E402

MODEL_ID = "cardiovanta-lr13"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj) -> None:
    path.write_bytes((json.dumps(obj, indent=2) + "\n").encode("utf-8"))


def random_inputs(n: int, order) -> pd.DataFrame:
    rng = np.random.default_rng(20261116)
    X = pd.DataFrame({
        "age": rng.uniform(1, 110, n), "sex": rng.integers(0, 2, n), "cp": rng.integers(0, 4, n),
        "trestbps": rng.uniform(50, 250, n), "chol": rng.uniform(80, 600, n), "fbs": rng.integers(0, 2, n),
        "restecg": rng.integers(0, 3, n), "thalach": rng.uniform(50, 230, n), "exang": rng.integers(0, 2, n),
        "oldpeak": rng.uniform(0, 8, n), "slope": rng.integers(0, 3, n), "ca": rng.integers(0, 5, n),
        "thal": rng.integers(0, 4, n)}).astype(float)
    return X[list(order)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-version", required=True)
    ap.add_argument("--target-version", required=True)
    args = ap.parse_args()
    root = (ROOT / "artifacts").resolve()
    src = load_model(MODEL_ID, args.source_version, registry_root=root)
    if src.metadata.serialization != "joblib":
        raise SystemExit("source must be a joblib-registered model")

    model_doc = P.export_calibrated_model(src.model)
    expl_doc = P.export_explanation_model(src.explanation_model)
    pm, pe = P.load_portable(json.loads(json.dumps(model_doc))), P.load_portable(json.loads(json.dumps(expl_doc)))

    X = random_inputs(50_000, src.model.feature_names_in_)
    mapping = {c: X[c].to_numpy() for c in X}
    d_proba = float(np.abs(src.model.predict_proba(X) - pm.predict_proba(mapping)).max())
    d_logit = float(np.abs(src.explanation_model.decision_function(X) - pe.decision_function(mapping)).max())
    print(f"parity on 50,000 inputs: max |dP| = {d_proba:.3e}, max |d log-odds| = {d_logit:.3e}")
    if d_proba > 1e-12 or d_logit > 1e-12:
        raise SystemExit("portable model does not reproduce the source model")

    tgt_art = root / f"model-{args.target_version}"
    tgt_entry = root / "models" / MODEL_ID / args.target_version
    for d in (tgt_art, tgt_entry):
        if d.exists():
            raise SystemExit(f"{d} exists; registered versions are immutable")
    tgt_art.mkdir(parents=True)
    tgt_entry.mkdir(parents=True)

    write_json(tgt_art / "model.json", model_doc)
    write_json(tgt_art / "explanation_model.json", expl_doc)
    shutil.copyfile(src.artifact_dir / "feature_schema.json", tgt_art / "feature_schema.json")
    shutil.copyfile(src.artifact_dir / "reference_predictions.csv", tgt_art / "reference_predictions.csv")
    bg = dict(src.shap_background)
    bg["metadata"] = dict(bg["metadata"], model_reference="explanation_model.json")
    write_json(tgt_art / "shap_background.json", bg)
    pkg = dict(src.package_metadata)
    pkg["package_version"] = args.target_version
    pkg["model_version"] = f"{pkg.get('model_version')} (portable)"
    pkg["serialization"] = {"format": P.PORTABLE_FORMAT, "exported_from": src.metadata.qualified_name,
                            "parity_max_abs_probability_difference": d_proba}
    write_json(tgt_art / "metadata.json", pkg)

    files = {"model": "model.json", "explanation_model": "explanation_model.json", "package_metadata": "metadata.json",
             "input_schema": "feature_schema.json", "shap_background": "shap_background.json",
             "reference_predictions": "reference_predictions.csv"}
    lines = [f"# SHA-256 manifest for {MODEL_ID}@{args.target_version} (sha256sum format).",
             f"# Files live in the registry's artifact_directory: artifacts/model-{args.target_version}/ (immutable once registered)."]
    lines += [f"{sha(tgt_art / f)}  {f}" for f in sorted(files.values())]
    (tgt_entry / "checksums.sha256").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    meta = json.loads(json.dumps(src.metadata.raw))
    meta["model_version"] = args.target_version
    meta["model_package_name"] = (f"CardioVanta production package {args.target_version}: portable (NumPy-only) export of "
                                  f"{src.metadata.qualified_name}, identical predictions")
    meta["artifact_directory"] = f"model-{args.target_version}"
    meta["artifacts"] = files
    meta["checksum_manifest_sha256"] = sha(tgt_entry / "checksums.sha256")
    meta["explanation"]["associated_model"] = f"{MODEL_ID}@{args.target_version}"
    meta["explanation"]["description"] = ("Uncalibrated LogisticRegression parameters exported from the "
                                          f"{src.metadata.qualified_name} explanation model; explains its own log-odds exactly.")
    meta["calibration"]["estimator"] = "cardiovanta_ml.inference.portable.PortableSigmoidCalibratedClassifier"
    meta["runtime"] = {"serialization": "portable_json", "format": P.PORTABLE_FORMAT,
                       "sklearn_version": src.metadata.sklearn_version,
                       "note": "Served with NumPy only. sklearn_version is the version the parameters were exported from."}
    meta["outcome_semantics"]["evidence"][-1] = meta["outcome_semantics"]["evidence"][-1].replace(
        src.metadata.model_version, args.target_version)
    meta["provenance"] = dict(meta["provenance"], exported_from=src.metadata.qualified_name,
                              export_script="scripts/research/export_portable_model.py",
                              parity_max_abs_probability_difference=d_proba,
                              registered=f"2026-11-16. Portable export of {src.metadata.qualified_name}; same fitted "
                                         "parameters, served without scikit-learn, SciPy or pandas.")
    write_json(tgt_entry / "metadata.json", meta)
    print(f"registered {MODEL_ID}@{args.target_version} in {tgt_entry.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
