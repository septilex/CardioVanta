"""
Portable (NumPy-only) form of CardioVanta's linear models.

A registered model whose ``runtime.serialization`` is ``"portable_json"`` stores its fitted parameters as JSON
instead of joblib pickles: the StandardScaler statistics, the one-hot categories, the logistic-regression
coefficients and, for the prediction model, the sigmoid calibrator. Serving it needs only NumPy, so the Vercel
function does not ship scikit-learn, SciPy or pandas (the main cause of its cold start).

The classes below reproduce exactly the computations scikit-learn 1.9.1 performs for these fitted objects:

* ``ColumnTransformer``: ``num`` = (x - mean_) / scale_, ``bin`` = x unchanged, ``cat`` = one-hot over the fitted
  ``categories_`` (unknown values encode as all zeros, ``handle_unknown="ignore"``), columns in that order;
* ``LogisticRegression.decision_function`` = X @ coef_.T + intercept_ (log-odds of ``classes_[1]``);
* ``CalibratedClassifierCV(method="sigmoid", ensemble=False)`` for two classes:
  P(classes_[1]) = expit(-(a * f + b)), P(classes_[0]) = 1 - P(classes_[1]).

They expose the attributes the registry and ``InferenceEngine`` already use (``classes_``, ``feature_names_in_``,
``named_steps``, ``predict_proba``, ``decision_function``, ``get_feature_names_out``), so the explanation code is
shared with the joblib path. Parity with the scikit-learn objects is tested in
``backend/tests/test_portable_model.py``. No pickle is ever loaded on this path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

PORTABLE_FORMAT = "cardiovanta.portable_linear.v1"


class PortableFormatError(ValueError):
    """A portable model document is malformed or internally inconsistent."""


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise PortableFormatError(message)


def _column(X: Any, name: str) -> np.ndarray:
    """One input column as float64. Accepts a mapping of name -> sequence (or a pandas DataFrame)."""
    try:
        values = X[name]
    except (KeyError, TypeError) as e:
        raise PortableFormatError(f"Input is missing feature {name!r}") from e
    if hasattr(values, "to_numpy"):
        values = values.to_numpy()
    return np.asarray(values, dtype=np.float64).reshape(-1)


def _expit(x: np.ndarray) -> np.ndarray:
    # scipy.special.expit's formula, 1 / (1 + exp(-x)); exp overflow gives inf and the correct limit 0.
    with np.errstate(over="ignore"):
        return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=np.float64)))


class PortablePreprocessor:
    """The fitted ColumnTransformer: scaled continuous, passthrough binary, one-hot categorical columns."""

    def __init__(self, spec: Mapping[str, Any]):
        _require(isinstance(spec, Mapping), "preprocessor must be an object")
        cont = spec.get("continuous") or {}
        self.continuous: List[str] = list(cont.get("features", []))
        self.mean = np.asarray(cont.get("mean", []), dtype=np.float64)
        self.scale = np.asarray(cont.get("scale", []), dtype=np.float64)
        _require(len(self.continuous) == self.mean.size == self.scale.size, "continuous features, mean and scale differ in length")
        _require(bool(np.all(np.isfinite(self.mean))) and bool(np.all(self.scale > 0)), "scaler statistics must be finite and positive")
        self.binary: List[str] = list((spec.get("binary") or {}).get("features", []))
        cats = (spec.get("categorical") or {}).get("features", [])
        self.categorical: List[str] = [c["feature"] for c in cats]
        self.categories: List[np.ndarray] = [np.asarray(c["categories"], dtype=np.float64) for c in cats]
        self._names = (
            [f"num__{f}" for f in self.continuous]
            + [f"bin__{f}" for f in self.binary]
            + [f"cat__{f}_{int(v) if float(v).is_integer() else v}" for f, cs in zip(self.categorical, self.categories) for v in cs]
        )
        declared = spec.get("feature_names_out")
        _require(list(declared or []) == self._names, "feature_names_out does not match the preprocessing specification")

    def get_feature_names_out(self) -> np.ndarray:
        return np.asarray(self._names, dtype=object)

    def transform(self, X: Any) -> np.ndarray:
        blocks = []
        if self.continuous:
            cont = np.column_stack([_column(X, f) for f in self.continuous])
            blocks.append((cont - self.mean) / self.scale)
        if self.binary:
            blocks.append(np.column_stack([_column(X, f) for f in self.binary]))
        for f, cats in zip(self.categorical, self.categories):
            col = _column(X, f)
            blocks.append((col[:, None] == cats[None, :]).astype(np.float64))
        return np.hstack(blocks)


class PortableLogisticRegression:
    def __init__(self, spec: Mapping[str, Any], n_features: int):
        self.coef_ = np.asarray([spec["coef"]], dtype=np.float64)
        self.intercept_ = np.asarray([spec["intercept"]], dtype=np.float64)
        self.classes_ = np.asarray(spec["classes"], dtype=np.int64)
        _require(self.coef_.shape == (1, n_features), f"coef must have {n_features} values")
        _require(self.classes_.shape == (2,), "a binary model needs exactly two classes")
        _require(bool(np.all(np.isfinite(self.coef_))) and bool(np.isfinite(self.intercept_[0])), "coefficients must be finite")


class PortablePipeline:
    """Preprocessor followed by logistic regression; the uncalibrated decision function."""

    def __init__(self, spec: Mapping[str, Any]):
        self.feature_names_in_ = np.asarray(spec["feature_names_in"], dtype=object)
        pre = PortablePreprocessor(spec["preprocessor"])
        lr = PortableLogisticRegression(spec["logistic_regression"], len(pre.get_feature_names_out()))
        expected_inputs = set(pre.continuous) | set(pre.binary) | set(pre.categorical)
        _require(expected_inputs == set(self.feature_names_in_), "preprocessor inputs do not match feature_names_in")
        self.named_steps: Dict[str, Any] = {"preprocessor": pre, "model": lr}
        self.classes_ = lr.classes_

    def decision_function(self, X: Any) -> np.ndarray:
        Xt = self.named_steps["preprocessor"].transform(X)
        lr = self.named_steps["model"]
        return (Xt @ lr.coef_.T + lr.intercept_).reshape(-1)

    def predict_proba(self, X: Any) -> np.ndarray:
        p1 = _expit(self.decision_function(X))
        return np.column_stack([1.0 - p1, p1])


class PortableSigmoidCalibratedClassifier:
    """CalibratedClassifierCV(method="sigmoid", ensemble=False) for two classes."""

    def __init__(self, spec: Mapping[str, Any]):
        self.base = PortablePipeline(spec["estimator"])
        cal = spec["calibrator"]
        _require(cal.get("method") == "sigmoid", "only sigmoid calibration is supported")
        self.a = float(cal["a"])
        self.b = float(cal["b"])
        _require(bool(np.isfinite(self.a)) and bool(np.isfinite(self.b)), "calibrator parameters must be finite")
        self.classes_ = self.base.classes_
        self.feature_names_in_ = self.base.feature_names_in_

    def predict_proba(self, X: Any) -> np.ndarray:
        f = self.base.decision_function(X)
        p1 = _expit(-(self.a * f + self.b))
        proba = np.column_stack([1.0 - p1, p1])
        proba[(1.0 < proba) & (proba <= 1.0 + 1e-5)] = 1.0
        return proba


def load_portable(document: Mapping[str, Any]) -> Any:
    """Build a portable model from its JSON document (already integrity-verified by the registry)."""
    _require(isinstance(document, Mapping), "portable model document must be an object")
    _require(document.get("format") == PORTABLE_FORMAT, f"unsupported portable format {document.get('format')!r}")
    kind = document.get("kind")
    if kind == "sigmoid_calibrated_logistic_regression":
        return PortableSigmoidCalibratedClassifier(document)
    if kind == "logistic_regression_pipeline":
        return PortablePipeline(document)
    raise PortableFormatError(f"unsupported portable model kind {kind!r}")


def is_portable(model: Any) -> bool:
    return isinstance(model, (PortablePipeline, PortableSigmoidCalibratedClassifier))


# ---------------------------------------------------------------------------
# Export (research tooling; needs scikit-learn, never used when serving)
# ---------------------------------------------------------------------------

def _export_pipeline(pipe: Any) -> Dict[str, Any]:
    pre = pipe.named_steps["preprocessor"]
    lr = pipe.named_steps["model"]
    spec: Dict[str, Any] = {"feature_names_in": [str(f) for f in pipe.feature_names_in_]}
    pspec: Dict[str, Any] = {}
    for name, transformer, cols in pre.transformers_:
        cols = [str(c) for c in cols]
        if name == "num":
            _require(transformer.with_mean and transformer.with_std, "StandardScaler must centre and scale")
            pspec["continuous"] = {"features": cols, "mean": [float(v) for v in transformer.mean_],
                                   "scale": [float(v) for v in transformer.scale_]}
        elif name == "bin":
            _require(getattr(transformer, "func", None) is None, "binary columns must pass through unchanged")
            pspec["binary"] = {"features": cols}
        elif name == "cat":
            _require(transformer.drop is None and transformer.handle_unknown == "ignore", "unsupported OneHotEncoder settings")
            pspec["categorical"] = {"features": [{"feature": c, "categories": [int(v) for v in cats]}
                                                 for c, cats in zip(cols, transformer.categories_)]}
        elif name == "remainder":
            _require(transformer == "drop", "remainder columns must be dropped")
        else:
            raise PortableFormatError(f"unsupported transformer {name!r}")
    pspec["feature_names_out"] = [str(n) for n in pre.get_feature_names_out()]
    spec["preprocessor"] = pspec
    spec["logistic_regression"] = {"coef": [float(v) for v in lr.coef_[0]], "intercept": float(lr.intercept_[0]),
                                   "classes": [int(c) for c in lr.classes_]}
    return spec


def export_explanation_model(pipe: Any) -> Dict[str, Any]:
    return {"format": PORTABLE_FORMAT, "kind": "logistic_regression_pipeline", **_export_pipeline(pipe)}


def export_calibrated_model(calibrated: Any) -> Dict[str, Any]:
    _require(type(calibrated).__name__ == "CalibratedClassifierCV", "expected a CalibratedClassifierCV")
    _require(calibrated.method == "sigmoid" and len(calibrated.calibrated_classifiers_) == 1,
             "only ensemble=False sigmoid calibration is portable")
    cc = calibrated.calibrated_classifiers_[0]
    _require(len(cc.calibrators) == 1, "a binary model has one calibrator")
    estimator = _export_pipeline(cc.estimator)
    return {
        "format": PORTABLE_FORMAT,
        "kind": "sigmoid_calibrated_logistic_regression",
        "classes": [int(c) for c in calibrated.classes_],
        "estimator": estimator,
        "calibrator": {"method": "sigmoid", "a": float(cc.calibrators[0].a_), "b": float(cc.calibrators[0].b_)},
    }


def feature_names(model: Any) -> Sequence[str]:
    return [str(f) for f in model.feature_names_in_]
