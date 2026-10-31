# Design: R3 — Deployment Reproducibility, CI & Model-Loading Hardening

## Runtime selection evidence
- **Supported versions.** Vercel docs (`/docs/functions/runtimes/python`, updated 2026-08-12) list 3.12 (default), 3.13 and 3.14. Python 3.12 was chosen because it is the platform default and all pinned dependencies install on it.
- **Clean 3.12.16 environment.** With the unchanged `api/requirements.txt`:
  - all 8 pre-R2 API snapshot responses were byte-identical;
  - scikit-learn's `InconsistentVersionWarning` was promoted to an error, and none was raised.
- **Pinned 3.12 environment.** With numpy 2.4.6 and scipy 1.17.1 pinned, the full synthetic suite passes: 518 tests. The same suite passes on 3.11.9.
- **Builder behaviour.** `@vercel/python-analysis` `discoverPythonPackage` walks up from `api/`. It stops at the first manifest (`api/requirements.txt`) and keeps only `.python-version` files inside that manifest's directory. A local `vercel build` printed "No Python version specified" with only a root file present, and "Using Python 3.12 from api\.python-version" after `api/.python-version` was added. It also confirmed "Installing required dependencies from api\requirements.txt".

## Legacy loader adapter
`ModelLoader(model_dir, model_id=None, model_version=None, registry_root=None).load_and_validate()`:
- Runs the original pre-load checks in the original order, with the same errors.
- Resolves the model identity explicitly. It uses either the caller's ID and version (both are required together), or the contract's single `model_label_mappings` record for the package version.
- Delegates to `load_model`, then requires the registered artifact directory to equal `model_dir`.
- Contains no `joblib.load` call. An AST scan of the production code allows deserialization only in `cardiovanta_ml/registry/loader.py`.

The research script `src/experiment/phase13/tabicl_statistical_audit.py` still calls `joblib.load` on the production artifact. It is a protected research script and is not part of the serving path, so it is unchanged and documented.

## Local Vercel build limits
- The local `vercel build` used a placeholder `.vercel/project.json`, because linking or pulling the real project could change account state or download secrets.
- On Windows the Python builder force-bundled Windows wheels ("without compatible wheels") and placed a 54 MB Linux `uv` binary in `_uv/` inside the project. It then failed with "Total bundle size (301.00 MB) exceeds the maximum function size (225 MB)".
- Project files account for about 1.3 MB; the rest is the numerical dependency stack, which was already deployed before R3. This cross-platform result is not a valid production verdict.
- A Linux `vercel build` with the real project settings remains an open verification item.

## R3.1: root cause of the 225 MB error (from `@vercel/python` 59.26.0 source)

### The two limits
- **Builder threshold (225 MB).** `LAMBDA_SIZE_THRESHOLD_BYTES = 225 MiB` is the builder's threshold for the zipped function. Above it, the builder externalizes public packages for runtime installation into `/tmp/_vc_deps`, within a 450 MiB budget out of 500 MiB of ephemeral storage. With `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` it bundles up to 5 GiB instead.
- **Documented limit (500 MB).** The docs give 500 MB uncompressed for Python and 5 GB for large functions (updated 2026-08-24). The two figures describe different stages of the same mechanism, so they don't contradict each other.

### Why packages get force-bundled
- A package can be externalized only if the lockfile has a wheel compatible with the target platform.
- The target uses the real glibc version only when `VERCEL_BUILD_IMAGE` is set on Linux, that is, inside Vercel's own build image. Everywhere else it falls back to `manylinux_2_17` x86_64.
- Per PyPI, the pinned numpy 2.4.6, scipy 1.17.1 and scikit-learn 1.9.1 ship only `manylinux_2_27` cp312 wheels, and pandas 3.0.6 only `manylinux_2_24`.
- Off Vercel's image they are therefore force-bundled, and the build fails above 225 MB.

### Consequences
- **Not Windows-specific.** The failure is expected on any Linux runner outside Vercel's build image, including GitHub Actions `ubuntu-latest`.
- **Not caused by the R3 pins.** The newer, previously unpinned versions have the same wheel tags.
- **Cold-start cost even on success.** On Vercel's own build image, the large packages would be externalized and installed at cold start, unless large functions are enabled.
