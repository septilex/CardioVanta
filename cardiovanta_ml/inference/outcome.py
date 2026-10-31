"""
Outcome semantics: which model label means "significant obstructive CAD present".

R2 note: the versioned registry (cardiovanta_ml.registry) is the production path. It
takes the disease label ONLY from each model's explicit registry metadata, which must
agree with the contract. ``resolve_disease_label`` below is kept for the legacy
package-directory validator (cardiovanta_ml.registry.legacy) and backward compatibility;
the registry never uses its interim fallback for newly registered models.

Every probability, threshold class and attribution returned by the production API
is expressed in DISEASE-POSITIVE orientation. This module resolves, for the
loaded model package, which training label denotes disease. Fail closed: a model
package whose orientation cannot be established must not be served.

Resolution order (``resolve_disease_label``)
--------------------------------------------
1. Explicit metadata (required for every future package, e.g. model v2)::

       "outcome_semantics": {
           "outcome": "significant_obstructive_cad_present",
           "disease_present_label": 1
       }

2. INTERIM legacy mapping for the frozen package 1.0.0 (R0.3 safety
   correction, 2026-10-31). Package 1.0.0 was trained in
   ``src/experiment/phase5.py`` on the raw ``target`` column of
   ``data/raw/heart.csv``. Phase 17 established, by 1-to-1 matching against UCI
   ``num``, that this column is inverted: target 1 = healthy (num == 0),
   target 0 = disease (num > 0). See
   ``reports/phase17_multicenter_validation.md`` and
   ``src/cardiovanta/data/external_loader.py::parse_cleveland_dev_cohort``.
   The frozen artifacts' coefficient signs agree. For this package the
   disease label is therefore 0. The artifacts themselves are NOT modified;
   their SHA-256 hashes are pinned in ``configs/artifact_hashes.json``.

3. Anything else is rejected with ``ValueError``.

Mathematics for the interim package
-----------------------------------
* ``CalibratedClassifierCV(method="sigmoid")`` with ``classes_ == [0, 1]`` fits
  one sigmoid per member for label 1 and defines P(label 0) = 1 - P(label 1).
  Hence P(disease) = predict_proba[:, index(label 0)] = 1 - P(healthy), exactly.
* The explanation model is an uncalibrated LogisticRegression. Its
  ``decision_function`` is the log-odds of ``classes_[1]``. The log-odds of the
  other label are exactly the negation, so contributions are multiplied by
  ``disease_log_odds_sign``. Additivity is preserved.
* The explanation model is NOT the calibrated ensemble. Its attributions are
  directional (strongly but not perfectly rank-concordant with the calibrated
  P(disease)) and must never be described as decomposing that probability.

When model v2 is trained on a harmonised target (disease = 1) with explicit
``outcome_semantics`` metadata, steps 2 and this interim note become unused
without any code change.
"""

from typing import Any, Mapping, Sequence

# Outcome semantics and the interim legacy label mapping are defined once, in the
# canonical contract (cardiovanta_ml/contracts/feature_schema.v2.json: "outcome" and
# "model_label_mappings"), and reach this module through the generated contract module.
from cardiovanta_ml.contracts.generated_features import (
    LEGACY_PACKAGE_DISEASE_LABELS,
    OUTCOME_ID,
    PROBABILITY_DEFINITION,
)

# Interim mapping for frozen packages that predate explicit outcome metadata
# (package_version -> disease-present label). Copied so tests can patch it.
LEGACY_PACKAGE_DISEASE_LABEL: dict[str, int] = dict(LEGACY_PACKAGE_DISEASE_LABELS)


def _validate_label(label: Any) -> int:
    if isinstance(label, bool) or label not in (0, 1):
        raise ValueError(f"disease_present_label must be 0 or 1, got {label!r}")
    return int(label)


def resolve_disease_label(metadata: Mapping[str, Any]) -> int:
    """Return the model label that denotes disease presence, or raise."""
    semantics = metadata.get("outcome_semantics")
    if semantics is not None:
        if semantics.get("outcome") != OUTCOME_ID:
            raise ValueError(
                f"outcome_semantics.outcome must be {OUTCOME_ID!r}, got {semantics.get('outcome')!r}"
            )
        return _validate_label(semantics.get("disease_present_label"))

    version = metadata.get("package_version")
    if version in LEGACY_PACKAGE_DISEASE_LABEL:
        return LEGACY_PACKAGE_DISEASE_LABEL[version]

    raise ValueError(
        f"Model package {version!r} does not declare outcome_semantics.disease_present_label; "
        "refusing to serve a model whose outcome orientation is unknown."
    )


def outcome_mapping_source(metadata: Mapping[str, Any]) -> str:
    """Human-readable provenance of the orientation used (exposed in API metadata)."""
    if metadata.get("outcome_semantics") is not None:
        return "explicit_package_metadata"
    return "interim_legacy_inverted_target_mapping"


def _binary_labels(classes: Sequence) -> list:
    labels = [int(c) for c in classes]
    if sorted(labels) != [0, 1]:
        raise ValueError(f"Expected binary classes [0, 1], got {labels}")
    return labels


def disease_label_index(classes: Sequence, disease_label: int) -> int:
    """Column of ``predict_proba`` holding P(disease present)."""
    return _binary_labels(classes).index(_validate_label(disease_label))


def disease_log_odds_sign(classes: Sequence, disease_label: int) -> float:
    """
    Factor converting a binary sklearn ``decision_function`` (log-odds of
    ``classes[1]``) into log-odds of disease presence.
    """
    labels = _binary_labels(classes)
    return 1.0 if labels[1] == _validate_label(disease_label) else -1.0
