# cardiovanta-ml

CardioVanta's research ML core, packaged independently of FastAPI and Next.js.
**Research use only. Not clinically validated.**

| Subpackage | Responsibility |
|---|---|
| `cardiovanta_ml.contracts` | Canonical clinical feature & outcome contract (`feature_schema.v2.json`, shipped as package data) and its generated Pydantic definitions (`generated_features.py`, do not edit) |
| `cardiovanta_ml.registry` | Versioned model registry: explicit ID and version, SHA-256 verification **before** deserialization, strict metadata/contract/outcome validation, one load per process |
| `cardiovanta_ml.inference` | `InferenceEngine`: P(significant obstructive CAD present), disease-positive thresholding, and explanation-model attributions |

## Usage

```python
from pathlib import Path
from cardiovanta_ml import load_model, predict, explain

model = load_model("cardiovanta-lr13", "1.0.0", registry_root=Path("/abs/path/to/artifacts"))
result = predict({"age": 55.0, "sex": 1, "cp": 2, ...}, model, threshold=None)
result["probability"]   # calibrated P(disease present)
```

The registry root must be an absolute path, passed explicitly or set in `CARDIOVANTA_MODEL_REGISTRY`. There is no default or "latest" model.

## Registry layout

```text
<registry root>/models/<model_id>/<model_version>/
    metadata.json        # identity, artifact roles, contract ref, class-label semantics, outcome mapping, ...
    checksums.sha256     # sha256sum-format manifest; its own hash is pinned in metadata.json
    model_card.md
<registry root>/<artifact_directory>/   # declared in metadata.json; must resolve inside the registry root
```

`cardiovanta-lr13@1.0.0` registers the original, unmodified artifacts in place (`artifact_directory: "model"`, i.e. `artifacts/model/`). The checksums, training script, CI integrity check and research code all reference that directory.

## Python runtimes

| Use | Python | Where pinned |
|---|---|---|
| **Production** (Vercel function `api/index.py`) | **3.12** | `api/.python-version`, which Vercel's builder reads; the root `.python-version` is ignored for `/api` functions |
| CI production job | 3.12 | root `.python-version` (`actions/setup-python` `python-version-file`) |
| Local development, research CI job | 3.11 | supported and tested (the full synthetic suite passes on both 3.11 and 3.12) |

Vercel supports 3.12 (default), 3.13 and 3.14; 3.11 is not available there. Package metadata: `requires-python = ">=3.11,<3.13"`.

Dependencies are pinned exactly in `api/requirements.txt` (the file Vercel installs) and in `backend/requirements.txt`: scikit-learn 1.9.1 (must equal the registered model's `runtime.sklearn_version`), and the model's transitive numerical stack numpy 2.4.6, scipy 1.17.1 and threadpoolctl 3.7.0.

## Installation and tests (reproducible path)

```powershell
py -3.12 -m venv .venv      # or 3.11 for local development
.venv\Scripts\python -m pip install -r backend/requirements.txt -r api/requirements.txt   # pinned FastAPI layer + runtime stack
.venv\Scripts\python -m pip install "./cardiovanta_ml[test]"                              # this package + pytest==9.1.1
.venv\Scripts\python contracts/codegen/generate.py --check
.venv\Scripts\python -m pytest backend/tests tests/test_monitoring.py tests/test_artifact_integrity.py
```

Set `CARDIOVANTA_RUN_INSTALL_TESTS=1` to also run the test that builds, installs and imports the package from a clean target directory.

### Verify a built wheel (as CI does)

```powershell
python -m pip wheel ./cardiovanta_ml --no-deps -w dist/
py -3.12 -m venv C:\tmp\wheel-venv
C:\tmp\wheel-venv\Scripts\python -m pip install dist\cardiovanta_ml-0.2.0-py3-none-any.whl
cd C:\tmp
C:\tmp\wheel-venv\Scripts\python -I <repo>\scripts\ci\verify_wheel_install.py --registry-root <repo>\artifacts --model-id cardiovanta-lr13 --model-version 1.0.0 --repo-root <repo>
```

## Test suites

| Suite | Data | Runs in |
|---|---|---|
| `backend/tests/`, `tests/test_monitoring.py`, `tests/test_artifact_integrity.py` | synthetic only | CI `verify-backend` (3.12) and locally |
| Other `tests/` modules (research phases) | read `data/raw/heart.csv`, some retrain in temporary directories | CI `research-data-tests` (3.11) only; deliberately not run during R0–R3 development |

## Deployment

- The Vercel Python function (`api/index.py`) imports the package from source.
- `vercel.json` `includeFiles` ships `cardiovanta_ml/**`.
- Runtime dependencies come from `api/requirements.txt`, confirmed by a local `vercel build`.
- The served model is pinned by `MODEL_ID` and `MODEL_VERSION`. An unregistered ID or version makes startup fail; there is no fallback.

## Regenerating the contract module

```powershell
python contracts/codegen/generate.py          # writes cardiovanta_ml/contracts/generated_features.py and src/types/generated-features.ts
python contracts/codegen/generate.py --check  # exit 1 when generated files are stale
```
