"""
R7-C1 tests: the calibration-slope reporting correction (reads only the saved R7 results JSON).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))
import r7_slope_reporting_correction as c1   # noqa: E402

SRC = (ROOT / "experiments" / "r7_slope_reporting_correction.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def record():
    return json.loads(c1.RESULTS.read_text(encoding="utf-8"))


def _original(record):
    return {k: v for k, v in record.items() if k != c1.BLOCK}


def test_original_results_preserved_and_hash_verified(record):
    assert c1.original_content_sha256(_original(record)) == c1.ORIGINAL_CONTENT_SHA256
    assert record[c1.BLOCK]["original_content_sha256_excluding_runtime"] == c1.ORIGINAL_CONTENT_SHA256
    assert list(record)[-1] == c1.BLOCK                       # appended after all original fields


def test_stored_correction_is_current_and_deterministic(record):
    rebuilt = c1.build(_original(record))
    assert json.dumps(rebuilt, sort_keys=True) == json.dumps(record[c1.BLOCK], sort_keys=True)


def test_preregistered_labels_unaffected(record):
    assert record[c1.BLOCK]["affects_preregistered_labels"] is False
    labels = {a: v["label"] for a, v in record["primary_nested_tuned_C"]["classification"]["per_arm"].items()}
    assert labels == {"B_no_slope": "inconclusive", "C_no_thal": "material_dependence",
                      "D_no_ca": "material_dependence", "E_no_slope_thal_ca": "material_dependence"}


def test_abs_deviation_convention_closer_to_one_is_better():
    comp = c1.abs_deviation_comparison([1.3, 1.3, 1.3], [0.8, 1.5, 1.1])
    assert comp["per_repeat"] == pytest.approx([-0.1, 0.2, -0.2])
    assert (comp["repeats_ablation_better"], comp["repeats_ablation_worse"], comp["repeats_tied"]) == (2, 1, 0)


def test_signed_slopes_flag_crossings_below_one():
    s = c1.signed_slope_summary([1.2, 0.95, 1.05], None)
    assert s["repeats_below_1"] == 1 and s["crosses_below_1"] is True and s["mean_below_1"] is False
    b = c1.signed_slope_summary([1.2, 1.1], {"ci95_low": 0.98, "ci95_high": 1.4})
    assert b["repeats_below_1"] == 0 and b["bootstrap_ci95_low_below_1"] is True and b["crosses_below_1"] is True


def test_superseded_fields_record_original_values(record):
    for analysis, arms in record[c1.BLOCK]["analyses"].items():
        for arm, e in arms.items():
            if arm == "A_baseline":
                continue
            sf = e["superseded_field"]
            original = record[analysis]["per_repeat_differences_vs_baseline"][arm]["calibration_slope"]["repeats_ablation_worse"]
            assert sf["original_value"] == original
            assert sf["corrected_value"] == e["abs_slope_minus_1_vs_baseline"]["per_repeat"]["repeats_ablation_worse"]


def test_refuses_to_annotate_altered_results(tmp_path, record):
    altered = _original(record)
    altered["primary_nested_tuned_C"]["arms"]["A_baseline"]["mean"]["roc_auc"] += 1e-9
    p = tmp_path / "r7.json"
    p.write_text(json.dumps(altered, indent=2), encoding="utf-8")
    with pytest.raises(RuntimeError, match="differs from the verified"):
        c1.apply(p)


def test_reads_no_dataset_and_fits_no_model():
    for forbidden in ("heart.csv", "read_csv", "dev_indices", "sklearn", "joblib", "load_development_data"):
        assert forbidden not in SRC, forbidden
