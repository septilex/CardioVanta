"""
CardioVanta R6 (provenance only): evidence record for the slope, thal and ca codebook mappings.

Design: openspec/changes/r6-feature-codebook-resolution/design.md

Reads documentation and project records only:
  * the UCI codebook text (data/external/raw/heart-disease.names), read as a document, never parsed as data
  * the clinical contract (read-only), the Phase 17 validation module and report, the external profiling report
  * a dated record of the public documentation checks (UCI dataset page loaded; Kaggle page HTTP 404)
No heart.csv row, locked observation or canonical Cleveland data file is read.
Statuses change only on E1 (patient-matched) or E2 (primary-source transformation) evidence.

Run:  python experiments/r6_codebook_evidence.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODEBOOK = PROJECT_ROOT / "data" / "external" / "raw" / "heart-disease.names"
CONTRACT = PROJECT_ROOT / "cardiovanta_ml" / "contracts" / "feature_schema.v2.json"
VALIDATION_MODULE = PROJECT_ROOT / "src" / "cardiovanta" / "data" / "validation.py"
PHASE17_REPORT = PROJECT_ROOT / "reports" / "phase17_multicenter_validation.md"
PROFILING = PROJECT_ROOT / "reports" / "external_data_profiling.json"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "r6_codebook_evidence.json"
CANONICAL_CLEVELAND_FILE = "processed.cleveland.data"

VERIFYING_LEVELS = {"E1", "E2"}
PUBLIC_DOCS = {   # retrieved 2026-10-31 via a read-only fetch of public pages
    "uci_dataset_page": {
        "url": "https://archive.ics.uci.edu/dataset/45/heart+disease", "retrieved": "2026-10-31", "loaded": True,
        "states_canonical_codes": {"slope": "1 upsloping, 2 flat, 3 downsloping", "ca": "number of major vessels (0-3)",
                                   "thal": "3 = normal; 6 = fixed defect; 7 = reversable defect"},
        "has_missing_values": "Yes (variables not identified in the retrieved text)",
        "missing_value_encoding_in_processed_files": "not stated",
        "documents_kaggle_recoding": False,
        "doi": "10.24432/C52P4X", "licence": "CC BY 4.0",
    },
    "kaggle_dataset_page": {
        "url": "https://www.kaggle.com/datasets/ronitf/heart-disease-uci", "retrieved": "2026-10-31", "loaded": False,
        "http_status": 404, "documents_kaggle_recoding": False,
        "note": "The commonly cited Kaggle source page is unavailable; the redistribution's recoding is undocumented by its publisher.",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def codebook_definitions(text: str) -> Dict[str, str]:
    """Canonical definitions as written in the UCI codebook (document text, not data)."""
    lines = text.splitlines()

    def block(start_pattern: str, n: int) -> str:
        idx = next(i for i, l in enumerate(lines) if re.search(start_pattern, l))
        return " ".join(l.strip() for l in lines[idx: idx + n])

    return {
        "slope": block(r"^\s*41 slope:", 4),
        "ca": block(r"^\s*44 ca:", 1),
        "thal": block(r"^\s*51 thal:", 1),
        "missing_values": block(r"Missing Attribute Values", 1),
        # the class-distribution row has five per-class counts plus a total (not the "Cleveland: 303" instance line)
        "cleveland_class_distribution": next(l.strip() for l in lines if re.search(r"^\s*Cleveland:\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+", l)),
    }


def contract_status(contract: Dict, feature: str, code: int) -> Dict:
    feat = next(f for f in contract["features"] if f["id"] == feature)
    opt = next(o for o in feat["options"] if o["code"] == code)
    return {"verification": opt["verification"], "clinical_meaning": opt["clinical_meaning"], "display_label": opt["display_label"]}


def build() -> Dict:
    codebook_text = CODEBOOK.read_text(encoding="utf-8", errors="replace")
    defs = codebook_definitions(codebook_text)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    validation_src = VALIDATION_MODULE.read_text(encoding="utf-8")
    phase17 = PHASE17_REPORT.read_text(encoding="utf-8")
    profiling = json.loads(PROFILING.read_text(encoding="utf-8"))["profiles"]

    phase17_matched_attributes = re.search(r"across five patient attributes \(([^)]*)\)", phase17).group(1)
    phase17_documented = {
        "cp": "KAGGLE_CP_TO_CANONICAL" in validation_src,
        "target": "1 - \\text{target}_{\\text{kaggle}}" in phase17,
        "slope": bool(re.search(r"KAGGLE_SLOPE|slope_to_canonical|SLOPE_TO_CANONICAL", validation_src)),
        "thal": bool(re.search(r"KAGGLE_THAL|thal_to_canonical|THAL_TO_CANONICAL", validation_src)),
        "ca": bool(re.search(r"KAGGLE_CA|ca_to_canonical|CA_TO_CANONICAL", validation_src)),
    }
    canonical_file_present = any(PROJECT_ROOT.rglob(CANONICAL_CLEVELAND_FILE)) or any(PROJECT_ROOT.rglob("heart+disease.zip"))
    external_sentinels = {p["cohort_name"]: {k: p["candidate_sentinel_counts"].get(k, {}) for k in ("slope", "ca", "thal")}
                          for p in profiling}

    common_evidence = [
        {"level": "E3", "source": "data/external/raw/heart-disease.names", "finding": defs},
        {"level": "E3", "source": PUBLIC_DOCS["uci_dataset_page"]["url"],
         "finding": "Canonical codes match the codebook; dataset 'has missing values'; processed-file missing encoding not stated; no Kaggle recoding documented."},
        {"level": "none", "source": PUBLIC_DOCS["kaggle_dataset_page"]["url"],
         "finding": "HTTP 404 on 2026-10-31: the redistribution's own documentation of its recoding is unavailable."},
        {"level": "none", "source": "reports/phase17_multicenter_validation.md; src/cardiovanta/data/validation.py",
         "finding": f"Phase 17 matched all Cleveland rows 1-to-1 on ({phase17_matched_attributes}) but recorded mappings only for cp and target; "
                    f"no slope/thal/ca cross-tabulation was documented (documented: {phase17_documented})."},
        {"level": "none", "source": "repository search",
         "finding": f"Canonical {CANONICAL_CLEVELAND_FILE} present locally: {canonical_file_present}. "
                    "Re-matching would require parsing canonical records of all 303 Cleveland patients, including the 61 locked observations, which R6 forbids."},
    ]

    def entry(feature, code, canonical_candidates, hypotheses, resolution_path):
        cs = contract_status(contract, feature, code)
        evidence = list(common_evidence)
        has_verifying = any(e["level"] in VERIFYING_LEVELS for e in evidence)
        resolved = cs["verification"] if not has_verifying else "REVIEW"   # no E1/E2 evidence exists -> unchanged
        return {
            "feature": feature, "production_code": code,
            "canonical_uci_source_codes": canonical_candidates,
            "contract_status": cs["verification"], "resolved_status": resolved,
            "clinical_meaning": cs["clinical_meaning"], "display_label_legacy": cs["display_label"],
            "confidence": "unresolved: no E1/E2 evidence",
            "evidence": evidence, "hypotheses_not_evidence": hypotheses, "resolution_path": resolution_path,
        }

    patient_match_path = ("Pre-registered patient-level match between the 242 development rows and canonical "
                          f"{CANONICAL_CLEVELAND_FILE}, using the Phase 17 matching keys; requires explicit authorisation, "
                          "because the canonical file also contains the locked patients' records. Alternatively, a primary-source "
                          "statement of the recoding from the dataset publisher (E2).")
    mappings: List[Dict] = []
    for code in (0, 1, 2):
        mappings.append(entry("slope", code, "one of {1 upsloping, 2 flat, 3 downsloping}; correspondence unknown",
                              ["Code 0..2 could be a shift of canonical 1..3 or a reordering (as happened for cp); the cp precedent shows a naive shift cannot be assumed."],
                              patient_match_path))
    for code in (1, 2, 3):
        mappings.append(entry("thal", code, "one of {3 normal, 6 fixed defect, 7 reversable defect}; correspondence unknown",
                              ["The 0..3 range implies a recoding of canonical {3, 6, 7}; the order is undocumented."],
                              patient_match_path))
    mappings.append(entry("thal", 0, "none defined; the canonical codebook has no thal code 0",
                          ["Secondary sources commonly describe Kaggle thal=0 as a recoded missing value; this is not documented in any project record or in the UCI page text retrieved, so it is not evidence."],
                          patient_match_path + " A match would show whether thal=0 rows correspond to missing canonical values."))
    for code in (0, 1, 2, 3):
        mappings.append(entry("ca", code, f"{code} (canonical ca is a vessel count 0-3)",
                              [], "Already supported at codebook_and_project_contract level; E1 matching would raise it to patient-matched."))
    mappings.append(entry("ca", 4, "none defined; the canonical codebook defines ca as 0-3",
                          ["Secondary sources commonly describe Kaggle ca=4 as a recoded missing value; not documented in any project record, so it is not evidence."],
                          patient_match_path + " A match would show whether ca=4 rows correspond to missing canonical values."))

    discrepancies = [{
        "item": "Cleveland num = 0 count",
        "codebook": defs["cleveland_class_distribution"],
        "phase17_report": "165 patients with canonical num == 0 and 138 with num > 0 (total 303)",
        "status": "Unresolved one-patient difference (codebook 164 vs Phase 17 165). Not investigated, because that would require Cleveland patient rows.",
    }]
    hygiene = [{
        "item": "Raw observation embedded in a report",
        "location": "reports/cardio_vanta_master_audit.md",
        "note": "An earlier audit report reproduces a raw heart.csv row (including ca=4). It was not used as evidence, and its partition was not checked.",
    }]
    consistent = all(m["resolved_status"] == m["contract_status"] for m in mappings)
    return {
        "experiment": "R6: clinical feature codebook resolution (provenance only)",
        "evidence_levels": {"E1": "patient-level matching (verifying)", "E2": "primary-source transformation statement (verifying)",
                            "E3": "canonical codebook definition only (non-verifying)", "E4": "secondary claims / distributions / coefficients (hypothesis only)"},
        "sources": {"codebook": {"path": "data/external/raw/heart-disease.names", "sha256": sha256(CODEBOOK)},
                    "contract": {"path": "cardiovanta_ml/contracts/feature_schema.v2.json", "sha256": sha256(CONTRACT)},
                    "public_documentation": PUBLIC_DOCS,
                    "external_cohort_documented_sentinels": external_sentinels},
        "mappings": mappings,
        "summary": {
            "codes_reviewed": len(mappings),
            "newly_verified": [f"{m['feature']}={m['production_code']}" for m in mappings if m["resolved_status"] != m["contract_status"]],
            "unresolved": [f"{m['feature']}={m['production_code']}" for m in mappings if m["resolved_status"] in ("unverified", "undefined_in_codebook")],
            "already_supported": [f"{m['feature']}={m['production_code']}" for m in mappings if m["resolved_status"] == "codebook_and_project_contract"],
            "consistent_with_contract": consistent,
            "data_rows_read": 0,
        },
        "discrepancies": discrepancies,
        "hygiene_notes": hygiene,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    record = build()
    if not record["summary"]["consistent_with_contract"]:
        raise SystemExit("Evidence record disagrees with the unchanged contract; review required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(record["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
