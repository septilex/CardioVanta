# CardioVanta Vercel Function Bundle Investigation (2026-11-03)

> **Status: NOT FIXED.** The 301 MB failure is a confirmed historical result of a local build. No compatible Linux Vercel build has run yet, so nothing here claims the problem is solved. No dependency, artifact or configuration was changed, and nothing was deployed.

## 1. The recorded failure

These are the two local `vercel build` runs (Windows host, Vercel CLI 59.26.0, 2026-10-31). Absolute local paths are omitted.

| Run | Key builder messages |
|---|---|
| 1 (12:35 IST) | "No Python version specified… Using python version: 3.12" · "Bundle size (265.17 MB) exceeds the standard size; optimizing dependencies." · "Error: Failed to prepare dependency tooling." |
| 2 (12:39 IST) | "Using Python 3.12 from api\.python-version" · "Installing required dependencies from uv.lock..." · **"Force-bundling 4 package(s) without compatible wheels: numpy, pandas, scikit-learn, scipy"** · "Downloading uv 0.10.11 (linux x86_64) for runtime dependency installation..." · "Bundle size (265.17 MB) exceeds the standard size; optimizing dependencies." · **"Total bundle size (301.00 MB) exceeds the maximum function size (225 MB) even after optimizing dependencies."** |

The excess was 76 MB over the 225 MB limit. The Linux build workflow (`.github/workflows/vercel-linux-build.yml`) has **never run**.

## 2. What is in the function

### 2.1 Project files

`vercel.json` `includeFiles` is `{artifacts/**,src/**,backend/**,configs/**,cardiovanta_ml/**}`. Sizes are from Git blob metadata.

| Path | Files | Size |
|---|---:|---:|
| `src/app` (TypeScript and CSS, not used by Python) | 8 | 279.9 KB |
| `backend` (including tests) | 28 | 158.6 KB |
| `src/experiment` (research) | 16 | 156.5 KB |
| `cardiovanta_ml` | 19 | 99.7 KB |
| `src/cardiovanta` (research loaders) | 4 | 67.0 KB |
| `artifacts` (model package and registry entry) | 9 | **58.5 KB** |
| Other `src/*`, `configs` | 13 | 35.1 KB |
| **Total** | **98** | **0.84 MB** |

The model itself is tiny: `model.joblib` is 27 KB. **Project files are not the problem.**

### 2.2 Python dependencies

These are the exact pins in `api/requirements.txt`. Each Linux wheel for CPython 3.12 x86_64 (manylinux) was downloaded and its uncompressed contents measured. Nothing was installed.

| Package | Installed size | Tests inside | Bundled native libraries | Why included | Needed by today's inference? | Can R8 eliminate it? | Risks of removing it |
|---|---:|---:|---:|---|---|---|---|
| **scipy** 1.17.1 | **108.97 MB** | 15.56 MB | 29.45 MB (OpenBLAS) | scikit-learn dependency; the pickled model's numerical stack | **Yes**: scikit-learn imports it | **Yes** | None for a portable runtime. Removing it from the current runtime breaks unpickling |
| **numpy** 2.4.6 | **53.92 MB** | 6.42 MB | 27.17 MB (OpenBLAS) | Arrays for scikit-learn and pandas | **Yes** | **Yes** (the stdlib runtime below needs none) | As above |
| **pandas** 3.0.6 | **37.14 MB** | 12.48 MB | — | `InferenceEngine._frame()` builds a one-row DataFrame, because the fitted `ColumnTransformer` selects columns by name | **Yes** (current code) | **Yes** | As above |
| **scikit-learn** 1.9.1 | **29.61 MB** | 5.59 MB | 0.24 MB | The pickled `CalibratedClassifierCV` and pipelines | **Yes** | **Yes** (export its parameters) | Exact parity must be proved per model version |
| joblib 1.6.0 | 0.88 MB | 0.33 MB | — | Deserialises the pickles (`registry/loader.py`) | Yes | **Yes** (JSON parameters need no pickle) | Removes the pickle code-execution risk too |
| threadpoolctl 3.7.0 | 0.09 MB | — | — | scikit-learn dependency | Indirectly | **Yes** | — |
| narwhals 2.28.0 | 1.98 MB | — | — | Required by scikit-learn (`narwhals>=2.0.1`) | Indirectly | **Yes** | — |
| cloudpickle 3.1.2 | 0.07 MB | — | — | Required by joblib | Indirectly | **Yes** | — |
| python-dateutil, tzdata | 0.87 MB | — | — | Required by pandas | Indirectly | **Yes** | — |
| pydantic-core 2.27.2, pydantic 2.10.4, pydantic-settings 2.7.1 | 6.34 MB | — | 4.40 MB | Request validation, settings | **Yes** | No | — |
| fastapi 0.141.1, starlette, anyio, idna, typing-*, annotated-*, python-dotenv | 2.22 MB | — | — | HTTP layer | **Yes** | No | — |
| **Total** | **242.10 MB** | **40.40 MB** | — | | | | |

- The **scientific stack** (numpy, scipy, scikit-learn, pandas, joblib, threadpoolctl) is **230.61 MB, 95% of all dependencies**.
- Its transitive helpers (narwhals, cloudpickle, dateutil, tzdata) add 2.9 MB.
- The web stack is about **8.6 MB**.

## 3. Reconciling 242 MB (Linux, measured) with 265 and 301 MB (Windows build)

| Observation | Interpretation | Confidence |
|---|---|---|
| The build ran on Windows; the builder said the four big packages had no compatible wheels and force-bundled them | On a Windows host the resolver chose Windows wheels. Those cannot be installed at runtime on Vercel's Linux, so they were packed into the bundle. Such binaries would also not run on Linux | **[L3] Inferred** from the log text |
| "Bundle size (265.17 MB)" before optimisation | The force-bundled packages plus the rest, at Windows wheel sizes | [L3] |
| Final total 301 MB, larger than 265 MB | The builder added Linux runtime-installation tooling ("Downloading uv 0.10.11 (linux x86_64) for runtime dependency installation") on top of the force-bundled packages. The uv binary is plausibly about 36 MB, though its size was not measured | [L3] / **[L4]** for the exact split |
| The build output (`.vercel/output`) was not retained | The exact file-by-file composition of the 301 MB **cannot be established now** | [L4] |

**What this means for a Linux build [L3]:**
- **If the builder externalises the scientific stack** (installs it at cold start, which manylinux wheels allow), the bundle may fit 225 MB. But every cold start would then download and install about 73 MB of compressed wheels: slower starts and a runtime dependency on package downloads. `scripts/ci/inspect_vercel_bundle.py` reports this as `runtime_install_mode`.
- **If it bundles everything**, dependencies alone are about 242 MB, above 225 MB, unless test folders (40 MB) are stripped.
- **Which one happens is unknown until R3.1 runs on Linux.**

## 4. Can the five-member ensemble run on a portable standard-library runtime?

**Yes.** This was demonstrated in this investigation with a read-only experiment:
- **Load.** `cardiovanta-lr13@1.0.0` was loaded through the verified registry, under the quarantine guard (0 refused accesses).
- **Export.** Its fitted parameters were exported to plain numbers:
  - for each of the 5 members: scaler means and scales, one-hot categories, 27 LR coefficients and the intercept, and the sigmoid calibrator's `a` and `b`;
  - the explanation model;
  - the 27 background means.
- **Recompute.** Inference was recomputed using **only Python's `math` module**.

| Check | Result |
|---|---|
| Members / method | 5 / sigmoid (`ensemble` = auto, i.e. per-fold) |
| Exported parameters | 8,014 bytes of JSON |
| Golden HIGH | scikit-learn 0.985790929097 · portable **0.985790929097** |
| Golden LOW | scikit-learn 0.016065905894 · portable **0.016065905894** |
| P(disease) over 20,002 profiles (golden pair plus 20,000 synthetic profiles across every accepted code and ±20% beyond the continuous development ranges) | Maximum absolute difference **2.2e-16** |
| Linear and SHAP-equivalent contributions over 2,002 profiles | Maximum absolute difference **0.0** for both |
| Speed (pure Python loop) | About 32 µs per profile |

The computation per member is:
1. standardise the five continuous inputs;
2. pass through the three binary inputs;
3. one-hot the five categorical inputs into 19 columns;
4. compute z = intercept + Σ coef·x;
5. calibrate: P(label 1) = 1 / (1 + exp(a·z + b)).

The five member values are averaged, and P(disease) = 1 − P(label 1), because the disease label is 0 for this model. Explanations are coef·x and coef·(x − mean), multiplied by −1 to give disease orientation.

**Consequence.** A portable runtime would remove numpy, scipy, pandas, scikit-learn, joblib and their helpers, about **233 MB**, leaving roughly **9 MB** of FastAPI and Pydantic. That is far below 225 MB. It would also remove pickle deserialisation from the serving path.

## 5. What R8 must still do (not done here)

1. **Pre-register parity criteria:** golden values, a synthetic grid, explanations and the tolerance.
2. **Keep `1.0.0` immutable.** Ship the exported parameters as a **new registered version** (for example `cardiovanta-lr13@1.1.0` or a new artifact role), with its own manifest, model card and contract mapping. Do not edit the existing registry entry.
3. **Generate the export from the verified pickles** in a reproducible script, and record its hash.
4. **Keep validation, orientation, range warnings and the response shape identical.** The existing golden and semantic tests must pass against both runtimes.
5. **Then prove it on Linux:** run `vercel-linux-build.yml` and confirm size, Python version, model load and no fallback with `inspect_vercel_bundle.py`. **Only a successful Linux Vercel build closes the 301 MB issue.**

## 6. Short-term options that keep the current runtime (not applied)

| Option | Expected effect | Caveat |
|---|---|---|
| Run R3.1 on Linux first | Establishes the real size and mode | Needs the owner's authorisation (it uses `production` environment secrets) |
| Narrow `includeFiles` (drop `src/app`, `src/experiment`, `src/cardiovanta`, `backend/tests`) | About 0.6 MB saved, which is **insufficient on its own** | Must keep the `src/inference` shims only if they are imported (serving does not import them) |
| Accept runtime dependency installation on Linux | May fit the limit | Slower, network-dependent cold starts |

None of these were applied.
