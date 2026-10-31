"""
Compatibility wrapper (R2). The implementation moved to ``cardiovanta_ml.inference.outcome``.

Re-exports the same objects (not copies), so ``LEGACY_PACKAGE_DISEASE_LABEL`` here
is the package's dict. New code should import from ``cardiovanta_ml``.
"""
from cardiovanta_ml.inference.outcome import (  # noqa: F401
    LEGACY_PACKAGE_DISEASE_LABEL,
    LEGACY_PACKAGE_DISEASE_LABELS,
    OUTCOME_ID,
    PROBABILITY_DEFINITION,
    disease_label_index,
    disease_log_odds_sign,
    outcome_mapping_source,
    resolve_disease_label,
)

__all__ = [
    "LEGACY_PACKAGE_DISEASE_LABEL", "LEGACY_PACKAGE_DISEASE_LABELS", "OUTCOME_ID", "PROBABILITY_DEFINITION",
    "disease_label_index", "disease_log_odds_sign", "outcome_mapping_source", "resolve_disease_label",
]
