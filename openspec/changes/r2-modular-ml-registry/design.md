# Design: R2 — Modular ML Package & Versioned Model Registry

## Package layout
```text
cardiovanta_ml/                  pyproject.toml (package-dir maps cardiovanta_ml -> "."), README.md, py.typed
  __init__.py                    lazy public API: load_model, predict, explain, InferenceEngine, ...
  config.py                      explicit registry root (argument or CARDIOVANTA_MODEL_REGISTRY, absolute only)
  contracts/                     feature_schema.v2.json (canonical), generated_features.py (generated), canonical.py (hash)
  inference/                     predict.py (InferenceEngine), explain.py, outcome.py
  registry/                      loader.py, metadata.py, integrity.py, exceptions.py, legacy.py (deprecated validator)
```
- The package root is placed at the repository root, so the existing `api/index.py` import path works unchanged.
- The `src/` namespace (which would allow duplicate imports) is avoided.

## Artifact placement decision
`artifacts/model/` is referenced by:
- the training script (`phase5.py`);
- the Phase 13 research scripts;
- the CI integrity check (`configs/artifact_hashes.json`);
- several tests;
- the R1 contract.

Moving or copying the binaries would create a second source of truth. The registry entry therefore declares `artifact_directory: "model"`, relative to the registry root `artifacts/`, and registers the existing files in place. Path safety is enforced relative to the registry root and the declared directory.

## Load sequence (fail closed)
1. Validate the model ID and exact semantic version.
2. Locate `<root>/models/<id>/<version>/` (no scanning, no "latest").
3. Validate the metadata strictly, and check its identity equals the request.
4. Check contract compatibility: name, version and SHA-256, plus that the bundled JSON hash equals the generated hash; feature order; outcome; and agreement with the contract's `model_label_mappings`. Interim mappings must be corroborated by the contract.
5. Resolve paths safely.
6. Check integrity:
   - the manifest's own SHA-256 matches the value pinned in the metadata;
   - the manifest set equals the declared artifacts;
   - every artifact matches its SHA-256.
7. Check that the runtime scikit-learn version equals the registered one.
8. Deserialize.
9. Run post-load checks:
   - classes and features of both models;
   - the disease label;
   - the input schema;
   - the package metadata version;
   - the explanation-model and SHAP-background association.
10. Cache the result per (root, id, version).

## Outcome mapping
- The clinical outcome is defined by the contract.
- The registry metadata maps artifact labels onto it (`class_label_semantics`, `outcome_semantics.disease_present_label`), with no implicit fallback.
- The legacy model declares label 0 as disease present and `mapping_status: interim_legacy`, which the contract corroborates.
- A future harmonised model declares `disease_present_label: 1` and `mapping_status: explicit`.

## Integrity guarantees
- The checks detect modification relative to the registered manifest.
- They are not signatures: they do not prove authenticity against a party who can rewrite the manifest and metadata consistently.

## Deployment
- The Vercel function imports the package from source.
- `includeFiles` adds `cardiovanta_ml/**`.
- `api/requirements.txt` already provides the runtime dependencies.
- `.gitattributes` pins LF for registry files, so the manifest hash is stable across checkouts.
