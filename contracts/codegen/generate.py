#!/usr/bin/env python3
"""
Deterministic code generator for the CardioVanta clinical feature & outcome contract.

Source:  cardiovanta_ml/contracts/feature_schema.v2.json   (canonical, ships with the ML package)
Outputs: cardiovanta_ml/contracts/generated_features.py   (Pydantic v2, part of the ML package)
         src/types/generated-features.ts                  (TypeScript, frontend)

Usage:
    python contracts/codegen/generate.py            # (re)generate outputs
    python contracts/codegen/generate.py --check    # exit 1 if outputs are stale

Exit codes: 0 = success / up to date, 1 = stale outputs (--check), 2 = invalid contract.

Standard library only (the canonical hash comes from the dependency-free
``cardiovanta_ml.contracts.canonical`` module). Output depends solely on the contract content, so repeated
runs are byte-identical. Files are always written with LF line endings, and the
check ignores CRLF conversion by Git on Windows.
"""
from __future__ import annotations

import argparse
import json
import pprint
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Single shared implementation of the canonical contract hash (stdlib-only module;
# the package __init__ is lazy, so this import pulls in no numpy/scikit-learn).
from cardiovanta_ml.contracts.canonical import contract_sha256  # noqa: E402

CONTRACT_REL = Path("cardiovanta_ml/contracts/feature_schema.v2.json")
PY_OUT_REL = Path("cardiovanta_ml/contracts/generated_features.py")
TS_OUT_REL = Path("src/types/generated-features.ts")

FEATURE_TYPES = {"continuous", "binary", "categorical"}
VERIFICATION_LEVELS_WITH_MEANING = {"verified_patient_matched", "codebook_and_project_contract"}
VERIFICATION_LEVELS_WITHOUT_MEANING = {"unverified", "undefined_in_codebook"}
VERIFICATION_LEVELS = VERIFICATION_LEVELS_WITH_MEANING | VERIFICATION_LEVELS_WITHOUT_MEANING
PACKAGE_STATUSES = {"interim_legacy", "explicit"}

TOP_KEYS = {"contract", "contract_version", "description", "compatible_model_input_schema",
            "evidence_sources", "verification_levels", "outcome", "model_label_mappings",
            "features", "feature_order"}
COMMON_FEATURE_KEYS = {"id", "label", "type", "description", "unit", "required",
                       "missing_value_policy", "evidence"}
CONTINUOUS_KEYS = COMMON_FEATURE_KEYS | {"unit_evidence", "accepted", "development_range"}
DISCRETE_KEYS = COMMON_FEATURE_KEYS | {"options"}
OPTION_KEYS = {"code", "display_label", "clinical_meaning", "verification", "canonical_uci_code"}


class ContractError(ValueError):
    """Raised when the source contract is malformed or uses unsupported definitions."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ContractError(msg)


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_keys(obj: dict, allowed: set, required: set, where: str) -> None:
    _require(isinstance(obj, dict), f"{where}: expected an object")
    unknown = set(obj) - allowed
    _require(not unknown, f"{where}: unsupported key(s) {sorted(unknown)}")
    missing = required - set(obj)
    _require(not missing, f"{where}: missing required key(s) {sorted(missing)}")


def validate_contract(c: Any) -> None:
    _check_keys(c, TOP_KEYS, {"contract", "contract_version", "outcome", "model_label_mappings",
                              "features", "feature_order", "verification_levels"}, "contract")
    _require(re.fullmatch(r"\d+\.\d+\.\d+", str(c["contract_version"])) is not None,
             "contract_version must be semantic MAJOR.MINOR.PATCH")
    _require(set(c["verification_levels"]) == VERIFICATION_LEVELS,
             f"verification_levels must define exactly {sorted(VERIFICATION_LEVELS)}")

    o = c["outcome"]
    _check_keys(o, {"id", "label", "clinical_definition", "positive", "negative", "output_probability",
                    "probability_definition", "evidence"},
                {"id", "label", "clinical_definition", "positive", "negative", "output_probability",
                 "probability_definition"}, "outcome")
    _require(re.fullmatch(r"[a-z][a-z0-9_]*", o["id"]) is not None, "outcome.id must be snake_case")
    _require(o["positive"].get("value") == 1 and o["positive"].get("meaning") == "disease_present",
             "outcome.positive must be value 1 / meaning 'disease_present'")
    _require(o["negative"].get("value") == 0 and o["negative"].get("meaning") == "disease_absent",
             "outcome.negative must be value 0 / meaning 'disease_absent'")
    _require(o["output_probability"] == "P(disease present)", "outcome.output_probability must be 'P(disease present)'")

    mlm = c["model_label_mappings"]
    _require(isinstance(mlm, dict) and isinstance(mlm.get("packages"), list), "model_label_mappings.packages must be a list")
    seen_pkgs = set()
    for i, p in enumerate(mlm["packages"]):
        where = f"model_label_mappings.packages[{i}]"
        _check_keys(p, {"model_id", "package_version", "artifact", "disease_present_label", "status", "reason", "evidence"},
                    {"model_id", "package_version", "disease_present_label", "status"}, where)
        _require(p["disease_present_label"] in (0, 1) and not isinstance(p["disease_present_label"], bool),
                 f"{where}.disease_present_label must be 0 or 1")
        _require(p["status"] in PACKAGE_STATUSES, f"{where}.status must be one of {sorted(PACKAGE_STATUSES)}")
        key = (p["model_id"], p["package_version"])
        _require(key not in seen_pkgs, f"{where}: duplicate package {key}")
        seen_pkgs.add(key)

    feats = c["features"]
    _require(isinstance(feats, list) and feats, "features must be a non-empty list")
    ids = []
    for f in feats:
        _require(isinstance(f, dict), "each feature must be an object")
        fid = f.get("id", "<missing id>")
        where = f"features[{fid}]"
        ftype = f.get("type")
        _require(ftype in FEATURE_TYPES, f"{where}: unsupported type {ftype!r}")
        allowed = CONTINUOUS_KEYS if ftype == "continuous" else DISCRETE_KEYS
        required = COMMON_FEATURE_KEYS - {"evidence"} | ({"accepted", "development_range"} if ftype == "continuous" else {"options"})
        _check_keys(f, allowed, required, where)
        _require(re.fullmatch(r"[a-z][a-z0-9_]*", fid) is not None, f"{where}: id must be snake_case")
        _require(_nonempty_str(f["label"]) and _nonempty_str(f["description"]), f"{where}: label and description required")
        _require(f["required"] is True, f"{where}: optional features are not supported")
        _require(f["missing_value_policy"] == "rejected", f"{where}: only missing_value_policy 'rejected' is supported")
        _require(f["unit"] is None or _nonempty_str(f["unit"]), f"{where}: unit must be a string or null")
        ids.append(fid)

        if ftype == "continuous":
            acc = f["accepted"]
            _check_keys(acc, {"finite_only", "min", "max"}, {"finite_only", "min", "max"}, f"{where}.accepted")
            _require(acc["finite_only"] is True, f"{where}: continuous features must be finite_only")
            for b in ("min", "max"):
                _require(acc[b] is None or _is_number(acc[b]), f"{where}.accepted.{b} must be a number or null")
            dr = f["development_range"]
            _require(_is_number(dr.get("min")) and _is_number(dr.get("max")) and dr["min"] < dr["max"],
                     f"{where}.development_range must have numeric min < max")
            _require(_nonempty_str(f.get("unit")), f"{where}: continuous features require a unit")
        else:
            opts = f["options"]
            _require(isinstance(opts, list) and opts, f"{where}: options must be a non-empty list")
            codes = []
            for o_ in opts:
                _check_keys(o_, OPTION_KEYS, {"code", "display_label", "clinical_meaning", "verification"}, f"{where}.options")
                code = o_["code"]
                _require(isinstance(code, int) and not isinstance(code, bool), f"{where}: option codes must be integers")
                _require(_nonempty_str(o_["display_label"]), f"{where}[{code}]: display_label required")
                lvl = o_["verification"]
                _require(lvl in VERIFICATION_LEVELS, f"{where}[{code}]: unknown verification {lvl!r}")
                if lvl in VERIFICATION_LEVELS_WITH_MEANING:
                    _require(_nonempty_str(o_["clinical_meaning"]), f"{where}[{code}]: verified options need clinical_meaning")
                else:
                    _require(o_["clinical_meaning"] is None,
                             f"{where}[{code}]: {lvl} options must not assert a clinical_meaning")
                codes.append(code)
            _require(len(set(codes)) == len(codes), f"{where}: duplicate option codes")
            _require(codes == sorted(codes), f"{where}: option codes must be in ascending order")
            if ftype == "binary":
                _require(codes == [0, 1], f"{where}: binary features must have codes [0, 1]")

    _require(len(set(ids)) == len(ids), f"duplicate feature ids: {sorted({i for i in ids if ids.count(i) > 1})}")
    _require(c["feature_order"] == ids, "feature_order must list every feature id exactly once, in features[] order")


def load_contract(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ContractError(f"cannot read contract {path}: {e}") from e
    try:
        contract = json.loads(text)
    except json.JSONDecodeError as e:
        raise ContractError(f"malformed JSON in {path}: {e}") from e
    validate_contract(contract)
    return contract



# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _pascal(fid: str) -> str:
    return "".join(part.capitalize() for part in fid.split("_"))


def _header(comment: str, contract: dict, digest: str) -> list[str]:
    return [
        f"{comment} AUTO-GENERATED by contracts/codegen/generate.py from {CONTRACT_REL.as_posix()}.",
        f"{comment} DO NOT EDIT BY HAND. Regenerate with: python contracts/codegen/generate.py",
        f"{comment} Contract: {contract['contract']} v{contract['contract_version']}",
        f"{comment} Contract SHA-256 (canonical JSON): {digest}",
    ]


def _field_description(f: dict) -> str:
    text = f"{f['label']}. {f['description']}"
    if f.get("unit"):
        text += f" Unit: {f['unit']}."
    if f["type"] != "continuous":
        parts = []
        for o in f["options"]:
            note = "" if o["verification"] in VERIFICATION_LEVELS_WITH_MEANING else f" [{o['verification']}]"
            parts.append(f"{o['code']} = {o['display_label']}{note}")
        text += " Codes: " + "; ".join(parts) + "."
    return text


def _feature_metadata(f: dict) -> dict:
    meta = {"id": f["id"], "label": f["label"], "type": f["type"], "description": f["description"],
            "unit": f["unit"], "required": f["required"], "missing_value_policy": f["missing_value_policy"]}
    if f["type"] == "continuous":
        meta["accepted"] = {"finite_only": True, "min": f["accepted"]["min"], "max": f["accepted"]["max"]}
        meta["development_range"] = {"min": f["development_range"]["min"], "max": f["development_range"]["max"]}
    else:
        meta["options"] = [
            {"code": o["code"], "display_label": o["display_label"], "clinical_meaning": o["clinical_meaning"],
             "verification": o["verification"]}
            for o in f["options"]
        ]
        meta["mapping_fully_verified"] = all(o["verification"] in VERIFICATION_LEVELS_WITH_MEANING for o in f["options"])
    return meta


def _outcome(contract: dict) -> dict:
    o = contract["outcome"]
    return {"id": o["id"], "label": o["label"], "clinical_definition": o["clinical_definition"],
            "positive": dict(o["positive"]), "negative": dict(o["negative"]),
            "output_probability": o["output_probability"], "probability_definition": o["probability_definition"]}


def _packages(contract: dict) -> list[dict]:
    return [{"model_id": p["model_id"], "package_version": p["package_version"],
             "disease_present_label": p["disease_present_label"], "status": p["status"]}
            for p in contract["model_label_mappings"]["packages"]]


# ---------------------------------------------------------------------------
# Python (Pydantic v2)
# ---------------------------------------------------------------------------

def _py_literal(obj: Any) -> str:
    return pprint.pformat(obj, width=100, sort_dicts=False)


def render_python(contract: dict) -> str:
    digest = contract_sha256(contract)
    feats = contract["features"]
    out = _header("#", contract, digest)
    out += [
        '"""Generated clinical feature & outcome contract definitions (Pydantic v2)."""',
        "from typing import Any, Dict, Literal, Tuple",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
        f"CONTRACT_NAME = {contract['contract']!r}",
        f"CONTRACT_VERSION = {contract['contract_version']!r}",
        f"CONTRACT_SHA256 = {digest!r}",
        "",
        f"FEATURE_ORDER: Tuple[str, ...] = {tuple(contract['feature_order'])!r}",
        "",
        "# Accepted model input codes per discrete feature (not a claim of verified meaning).",
    ]
    for f in feats:
        if f["type"] != "continuous":
            codes = ", ".join(str(o["code"]) for o in f["options"])
            out.append(f"{_pascal(f['id'])}Code = Literal[{codes}]")
    out += [
        "",
        "# Clinical outcome semantics (domain definition, independent of any model artifact).",
        f"OUTCOME: Dict[str, Any] = {_py_literal(_outcome(contract))}",
        f"OUTCOME_ID = {contract['outcome']['id']!r}",
        f"OutcomeId = Literal[{contract['outcome']['id']!r}]",
        f"PROBABILITY_DEFINITION = {contract['outcome']['probability_definition']!r}",
        "",
        "# Artifact-specific label mappings (model metadata, NOT the outcome definition).",
        f"MODEL_LABEL_MAPPINGS: Tuple[Dict[str, Any], ...] = {_py_literal(tuple(_packages(contract)))}",
        "",
        "# package_version -> disease-present label, for interim legacy packages only.",
        "LEGACY_PACKAGE_DISEASE_LABELS: Dict[str, int] = {",
    ]
    for p in _packages(contract):
        if p["status"] == "interim_legacy":
            out.append(f"    {p['package_version']!r}: {p['disease_present_label']},")
    out += [
        "}",
        "",
        "# Full per-feature metadata, keyed by feature id, in FEATURE_ORDER.",
        f"FEATURES: Dict[str, Dict[str, Any]] = {_py_literal({f['id']: _feature_metadata(f) for f in feats})}",
        "",
        "",
        "class ClinicalFeaturesBase(BaseModel):",
        '    """The production clinical inputs, in FEATURE_ORDER. All required; unknown fields rejected."""',
        "",
        '    model_config = ConfigDict(extra="forbid")',
        "",
    ]
    for f in feats:
        desc = _field_description(f)
        if f["type"] == "continuous":
            out.append(f"    {f['id']}: float = Field(allow_inf_nan=False, description={desc!r})")
        else:
            out.append(f"    {f['id']}: {_pascal(f['id'])}Code = Field(description={desc!r})")
    out += [
        "",
        "",
        "class FeatureContributionsBase(BaseModel):",
        '    """One additive contribution per production feature, in FEATURE_ORDER."""',
        "",
        '    model_config = ConfigDict(extra="forbid")',
        "",
    ]
    out += [f"    {f['id']}: float" for f in feats]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# TypeScript
# ---------------------------------------------------------------------------

def _ts_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def render_typescript(contract: dict) -> str:
    digest = contract_sha256(contract)
    feats = contract["features"]
    discrete = [f for f in feats if f["type"] != "continuous"]
    out = _header("//", contract, digest)
    out += [
        "/* eslint-disable */",
        "",
        f"export const CONTRACT_NAME = {json.dumps(contract['contract'])} as const;",
        f"export const CONTRACT_VERSION = {json.dumps(contract['contract_version'])} as const;",
        f"export const CONTRACT_SHA256 = {json.dumps(digest)} as const;",
        "",
        f"export const FEATURE_ORDER = {json.dumps(contract['feature_order'])} as const;",
        "export type FeatureId = (typeof FEATURE_ORDER)[number];",
        "",
        "export type MappingVerification =",
        *[f'  | "{lvl}"' for lvl in sorted(VERIFICATION_LEVELS)],
        "  ;",
        "",
        "/** Accepted model input codes per discrete feature (not a claim of verified meaning). */",
    ]
    for f in discrete:
        out.append(f"export type {_pascal(f['id'])}Code = {' | '.join(str(o['code']) for o in f['options'])};")
    out += ["", "/** The production clinical inputs (request body of POST /api/v1/predict). */",
            "export interface ClinicalFeatures {"]
    for f in feats:
        ts_type = "number" if f["type"] == "continuous" else f"{_pascal(f['id'])}Code"
        unit = f" ({f['unit']})" if f.get("unit") else ""
        out.append(f"  /** {f['label']}{unit} */")
        out.append(f"  {f['id']}: {ts_type};")
    out += ["}", "",
            "export type CategoricalFeatureId = " + " | ".join(f'"{f["id"]}"' for f in discrete) + ";",
            "export type ContinuousFeatureId = Exclude<FeatureId, CategoricalFeatureId>;",
            "",
            "export interface CategoricalOption {",
            "  readonly code: number;",
            "  /** Text shown in the UI. For unverified codes this is a legacy label, not a verified meaning. */",
            "  readonly display_label: string;",
            "  /** Verified clinical meaning, or null when not established. */",
            "  readonly clinical_meaning: string | null;",
            "  readonly verification: MappingVerification;",
            "}",
            "",
            "export interface InputConstraint {",
            "  readonly finite_only: true;",
            "  readonly min: number | null;",
            "  readonly max: number | null;",
            "}",
            "",
            "export interface DevelopmentRange {",
            "  readonly min: number;",
            "  readonly max: number;",
            "}",
            "",
            "export interface FeatureMetadata {",
            "  readonly id: FeatureId;",
            "  readonly label: string;",
            '  readonly type: "continuous" | "binary" | "categorical";',
            "  readonly description: string;",
            "  readonly unit: string | null;",
            "  readonly required: boolean;",
            "  readonly missing_value_policy: string;",
            "  readonly accepted?: InputConstraint;",
            "  readonly development_range?: DevelopmentRange;",
            "  readonly options?: readonly CategoricalOption[];",
            "  readonly mapping_fully_verified?: boolean;",
            "}",
            "",
            f"export const FEATURE_METADATA: Readonly<Record<FeatureId, FeatureMetadata>> = "
            f"{_ts_json({f['id']: _feature_metadata(f) for f in feats})};",
            "",
            f"export const CATEGORICAL_OPTIONS: Readonly<Record<CategoricalFeatureId, readonly CategoricalOption[]>> = "
            f"{_ts_json({f['id']: _feature_metadata(f)['options'] for f in discrete})};",
            "",
            "/** code -> display label, per discrete feature. */",
            f"export const CATEGORICAL_LABELS: Readonly<Record<CategoricalFeatureId, Readonly<Record<number, string>>>> = "
            f"{_ts_json({f['id']: {str(o['code']): o['display_label'] for o in f['options']} for f in discrete})};",
            "",
            f"export const INPUT_CONSTRAINTS: Readonly<Record<ContinuousFeatureId, InputConstraint>> = "
            f"{_ts_json({f['id']: _feature_metadata(f)['accepted'] for f in feats if f['type'] == 'continuous'})};",
            "",
            f"export const DEVELOPMENT_RANGES: Readonly<Record<ContinuousFeatureId, DevelopmentRange>> = "
            f"{_ts_json({f['id']: _feature_metadata(f)['development_range'] for f in feats if f['type'] == 'continuous'})};",
            "",
            "/** Clinical outcome semantics: the API probability is P(disease present). */",
            f"export const OUTCOME = {_ts_json(_outcome(contract))} as const;",
            "export type OutcomeId = typeof OUTCOME.id;",
            ]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render_all(contract: dict) -> dict[Path, str]:
    return {PY_OUT_REL: render_python(contract), TS_OUT_REL: render_typescript(contract)}


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--check", action="store_true", help="fail (exit 1) if generated files are missing or stale")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (default: auto-detected)")
    parser.add_argument("--contract", type=Path, default=None, help="contract path (default: <root>/contracts/feature_schema.v2.json)")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    contract_path = args.contract if args.contract else root / CONTRACT_REL
    try:
        contract = load_contract(contract_path)
    except ContractError as e:
        print(f"ERROR: invalid contract: {e}", file=sys.stderr)
        return 2

    outputs = render_all(contract)
    if args.check:
        stale = []
        for rel, content in outputs.items():
            path = root / rel
            if not path.exists() or _normalise(path.read_text(encoding="utf-8")) != content:
                stale.append(rel.as_posix())
        if stale:
            print("STALE generated files (run: python contracts/codegen/generate.py):", file=sys.stderr)
            for s in stale:
                print(f"  - {s}", file=sys.stderr)
            return 1
        print(f"OK: generated files are up to date with contract v{contract['contract_version']}")
        return 0

    for rel, content in outputs.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print(f"wrote {rel.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
