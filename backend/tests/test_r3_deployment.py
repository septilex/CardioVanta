"""
R3 tests: production runtime pinning, deployment packaging, centralized model loading and CI enforcement.

All inputs are synthetic. ``data/raw/heart.csv`` is never opened. Packaging
checks inspect configuration files and copy only the function bundle.
"""
import ast
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import joblib
import pytest

from cardiovanta_ml import clear_model_cache, load_model
from cardiovanta_ml.registry import IntegrityError, RegistryError

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_ROOT = ROOT / "artifacts"
ENTRY_REL = Path("models") / "cardiovanta-lr13" / "1.0.0"
VERCEL_SUPPORTED_PYTHON = {"3.12", "3.13", "3.14"}  # vercel.com/docs/functions/runtimes/python (2026-08-12)
HIGH_RISK = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
                 thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)


def _requirements(path):
    pins = {}
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, _, version = line.partition("==")
            assert version, f"{path}: unpinned requirement {line!r}"
            pins[name.lower()] = version
    return pins


# =============================================================================
# Runtime pinning
# =============================================================================

def test_production_python_runtime_is_pinned_and_vercel_supported():
    version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert version == "3.12"
    assert version in VERCEL_SUPPORTED_PYTHON
    # Vercel's Python builder (@vercel/python-analysis discoverPythonPackage) walks up from the
    # entrypoint dir, stops at the first manifest (api/requirements.txt) and only honours a
    # .python-version inside that manifest's directory. A root-level file alone is ignored, as
    # verified with a local `vercel build` ("Using Python 3.12 from api\.python-version").
    assert (ROOT / "api" / ".python-version").read_text(encoding="utf-8").strip() == version
    assert not (ROOT / "api" / "pyproject.toml").exists(), "a generated api/pyproject.toml would change dependency resolution"
    project = tomllib.loads((ROOT / "cardiovanta_ml" / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == ">=3.11,<3.13"  # production 3.12 + local-dev 3.11
    assert sys.version_info[:2] in ((3, 11), (3, 12)), "tests must run on a supported runtime"


def test_deployed_dependencies_are_fully_pinned_and_model_compatible():
    api = _requirements("api/requirements.txt")
    for pkg in ("fastapi", "pydantic", "pydantic-settings", "joblib", "scikit-learn", "pandas",
                "numpy", "scipy", "threadpoolctl"):
        assert pkg in api, f"api/requirements.txt must pin {pkg}"
    meta = json.loads((REGISTRY_ROOT / ENTRY_REL / "metadata.json").read_text(encoding="utf-8"))
    assert api["scikit-learn"] == meta["runtime"]["sklearn_version"] == "1.9.1"
    # Backend/CI requirements and the ML package declare the same versions as the deployed function.
    backend = _requirements("backend/requirements.txt")
    research = _requirements("requirements.txt")
    pkg_deps = {d.split("==")[0].lower(): d.split("==")[1]
                for d in tomllib.loads((ROOT / "cardiovanta_ml" / "pyproject.toml").read_text())["project"]["dependencies"]}
    for name in ("numpy", "scipy", "joblib", "scikit-learn", "pandas"):
        assert api[name] == pkg_deps[name], name
    for name in set(api) & set(backend):
        assert api[name] == backend[name], name
    for name in ("numpy", "scipy", "threadpoolctl", "joblib", "scikit-learn", "pandas"):
        assert api[name] == research[name], name


def test_installed_runtime_matches_pins():
    import numpy, pandas, scipy, sklearn
    api = _requirements("api/requirements.txt")
    assert sklearn.__version__ == api["scikit-learn"]
    assert numpy.__version__ == api["numpy"] and scipy.__version__ == api["scipy"]
    assert pandas.__version__ == api["pandas"]


# =============================================================================
# Deployment packaging (configuration-level and bundle-level)
# =============================================================================

def _ignore_patterns():
    return [l.strip() for l in (ROOT / ".vercelignore").read_text().splitlines() if l.strip() and not l.startswith("#")]


def _ignored(rel: Path, patterns) -> bool:
    return any(fnmatch.fnmatch(part, pat) for part in rel.parts for pat in patterns)


def test_vercelignore_excludes_locked_derived_results():
    """Locked-derived research outputs are never uploaded by the Vercel CLI: each one is either under an
    ignored directory (e.g. reports/) or listed by its exact, root-anchored path."""
    spec = importlib.util.spec_from_file_location("dq_policy", ROOT / "scripts" / "ci" / "data_quarantine.py")
    dq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dq)
    patterns = _ignore_patterns()
    for rel in dq.LOCKED_DERIVED + dq.LOCKED_SOURCES:
        assert _ignored(Path(rel), patterns) or "/" + rel in patterns, f".vercelignore would upload {rel}"


def test_vercel_config_includes_runtime_resources():
    vercel = json.loads((ROOT / "vercel.json").read_text())
    include = vercel["functions"]["api/**/*.py"]["includeFiles"].strip("{}").split(",")
    for needed in ("artifacts/**", "backend/**", "src/**", "configs/**", "cardiovanta_ml/**"):
        assert needed in include
    patterns = _ignore_patterns()
    required = [
        "api/index.py", "api/requirements.txt",
        "cardiovanta_ml/contracts/feature_schema.v2.json", "cardiovanta_ml/contracts/generated_features.py",
        "cardiovanta_ml/registry/loader.py", "cardiovanta_ml/inference/predict.py",
        f"artifacts/{ENTRY_REL.as_posix()}/metadata.json", f"artifacts/{ENTRY_REL.as_posix()}/checksums.sha256",
        f"artifacts/{ENTRY_REL.as_posix()}/model_card.md",
        "artifacts/model/model.joblib", "artifacts/model/explanation_model.joblib",
        "artifacts/model/metadata.json", "artifacts/model/feature_schema.json",
        "artifacts/model/shap_background.json", "artifacts/model/reference_predictions.csv",
        "backend/app/main.py", "backend/app/core/config.py", "src/config/config.py",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), rel
        assert not _ignored(Path(rel), patterns), f".vercelignore would exclude {rel}"
    assert _ignored(Path("data/raw/heart.csv"), patterns), "raw data must stay out of the deployment"


def _bundle(dest):
    vercel = json.loads((ROOT / "vercel.json").read_text())
    tops = [g.split("/")[0] for g in vercel["functions"]["api/**/*.py"]["includeFiles"].strip("{}").split(",")] + ["api"]
    patterns = _ignore_patterns()
    for top in tops:
        for path in (ROOT / top).rglob("*"):
            rel = path.relative_to(ROOT)
            if path.is_file() and not _ignored(rel, patterns) and "__pycache__" not in rel.parts:
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest / rel)


def _run(code, cwd, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "MODEL_ID", "MODEL_VERSION", "MODEL_REGISTRY_ROOT", "CARDIOVANTA_MODEL_REGISTRY")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)


_BUNDLE_PROBE = (
    "import sys, os, json\n"
    "sys.path.insert(0, os.getcwd())\n"
    "from api.index import app\n"
    "from backend.app.core.config import settings\n"
    "from fastapi.testclient import TestClient\n"
    "with TestClient(app) as c:\n"
    "    r = c.post('/api/v1/predict', json=%r)\n"
    "    eng = app.state.inference_engine\n"
    "    print('PROBE ' + json.dumps({'status': r.status_code, 'p': round(r.json()['prediction']['probability'], 4),\n"
    "        'root': str(settings.MODEL_REGISTRY_ROOT.resolve()), 'artifact_dir': str(eng.loaded.artifact_dir),\n"
    "        'entry_dir': str(eng.loaded.entry_dir), 'model': eng.loaded.metadata.qualified_name,\n"
    "        'legacy_imported': 'cardiovanta_ml.registry.legacy' in sys.modules}))\n"
) % (HIGH_RISK,)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    dest = tmp_path_factory.mktemp("vercel_bundle")
    _bundle(dest)
    return dest


def _probe(bundle, env_extra=None):
    r = _run(_BUNDLE_PROBE, cwd=bundle, env_extra=env_extra)
    lines = [l[6:] for l in r.stdout.splitlines() if l.startswith("PROBE ")]
    return r, (json.loads(lines[0]) if lines else None)


def test_bundle_resolves_registry_inside_function_and_serves_pinned_model(bundle):
    r, probe = _probe(bundle)
    assert r.returncode == 0, r.stderr[-2000:]
    root = bundle.resolve()
    assert probe["status"] == 200 and probe["p"] == 0.9858
    assert probe["model"] == "cardiovanta-lr13@1.0.0"
    assert Path(probe["root"]) == root / "artifacts"                    # registry root inside the bundle
    assert Path(probe["artifact_dir"]) == root / "artifacts" / "model"
    assert Path(probe["entry_dir"]) == root / "artifacts" / ENTRY_REL
    assert probe["legacy_imported"] is False                             # serving never touches the legacy adapter


@pytest.mark.parametrize("env", [{"MODEL_VERSION": "1.0.1"}, {"MODEL_VERSION": "9.9.9"},
                                 {"MODEL_VERSION": "latest"}, {"MODEL_ID": "cardiovanta-lr14"}])
def test_bundle_never_falls_back_to_another_model(bundle, env):
    r, probe = _probe(bundle, env_extra=env)
    assert probe is None and r.returncode != 0
    assert "ModelNotRegisteredError" in r.stderr or "is not registered" in r.stderr or "Invalid model version" in r.stderr


def test_environment_config_pins_explicit_model():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^MODEL_ID=cardiovanta-lr13$", env_example, re.M)
    assert re.search(r"^MODEL_VERSION=1\.0\.0$", env_example, re.M)
    from backend.app.core.config import settings
    assert (settings.MODEL_ID, settings.MODEL_VERSION) == ("cardiovanta-lr13", "1.0.0")


# =============================================================================
# Centralized deserialization / legacy loader hardening
# =============================================================================

_LOAD_CALLS = {("joblib", "load"), ("pickle", "load"), ("pickle", "loads"), ("cloudpickle", "load"),
               ("cloudpickle", "loads"), ("dill", "load"), ("dill", "loads")}
PRODUCTION_CODE = ["cardiovanta_ml", "backend/app", "api", "src/inference", "src/config", "scripts"]


def _deserialization_sites(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if (node.func.value.id, node.func.attr) in _LOAD_CALLS:
                yield node.lineno
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            if isinstance(node, ast.ImportFrom) and node.module in ("joblib", "pickle") and "load" in names:
                yield node.lineno


def test_model_deserialization_is_centralized_in_registry_loader():
    sites = {}
    for top in PRODUCTION_CODE:
        for py in (ROOT / top).rglob("*.py"):
            rel_parts = py.relative_to(ROOT).parts
            if any(p in ("build", "dist") or p.endswith(".egg-info") for p in rel_parts):
                continue  # setuptools build staging copies (gitignored), not source
            lines = list(_deserialization_sites(py))
            if lines:
                sites[py.relative_to(ROOT).as_posix()] = lines
    assert set(sites) == {"cardiovanta_ml/registry/loader.py"}, sites
    legacy_src = (ROOT / "cardiovanta_ml" / "registry" / "legacy.py").read_text(encoding="utf-8")
    assert "import joblib" not in legacy_src and "load_model(" in legacy_src


@pytest.fixture
def fresh_cache():
    clear_model_cache()
    yield
    clear_model_cache()


def test_legacy_loader_delegates_to_verified_registry(fresh_cache):
    from backend.app.core.model_loader import ModelLoader
    package = ModelLoader(model_dir=ROOT / "artifacts" / "model").load_and_validate()
    registered = load_model("cardiovanta-lr13", "1.0.0", registry_root=REGISTRY_ROOT)
    assert package.model is registered.model and package.explanation_model is registered.explanation_model
    assert package.metadata == registered.package_metadata and package.feature_schema == registered.input_schema


@pytest.fixture
def tmp_registry(tmp_path, fresh_cache):
    root = tmp_path / "artifacts"
    shutil.copytree(REGISTRY_ROOT / "model", root / "model")
    shutil.copytree(REGISTRY_ROOT / ENTRY_REL, root / ENTRY_REL)
    return root


def test_legacy_loader_cannot_deserialize_tampered_artifacts(tmp_registry, monkeypatch):
    from backend.app.core.model_loader import ModelLoader
    calls = []
    monkeypatch.setattr(joblib, "load", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(AssertionError("unchecked load")))
    model_path = tmp_registry / "model" / "model.joblib"
    model_path.write_bytes(model_path.read_bytes() + b"tamper")
    with pytest.raises(IntegrityError, match="SHA-256 mismatch"):
        ModelLoader(model_dir=tmp_registry / "model").load_and_validate()
    assert calls == []


def test_legacy_loader_rejects_unregistered_directory(tmp_path, fresh_cache):
    """A valid-looking legacy directory that is not a registered model cannot be loaded."""
    from backend.app.core.model_loader import ModelLoader
    plain = tmp_path / "loose_model"
    shutil.copytree(REGISTRY_ROOT / "model", plain)
    with pytest.raises(RegistryError):
        ModelLoader(model_dir=plain).load_and_validate()


def test_legacy_loader_requires_explicit_identity_pairs(fresh_cache):
    from backend.app.core.model_loader import ModelLoader
    with pytest.raises(ValueError, match="both model_id and model_version"):
        ModelLoader(model_dir=ROOT / "artifacts" / "model", model_id="cardiovanta-lr13").load_and_validate()
    with pytest.raises(RegistryError):
        ModelLoader(model_dir=ROOT / "artifacts" / "model", model_id="cardiovanta-lr13",
                    model_version="9.9.9").load_and_validate()


def test_backend_import_does_not_load_legacy_adapter(tmp_path):
    r = _run("import sys; import backend.app.main; print('legacy' if 'cardiovanta_ml.registry.legacy' in sys.modules else 'clean')",
             cwd=ROOT)
    assert r.returncode == 0, r.stderr[-1500:]
    assert r.stdout.strip().splitlines()[-1] == "clean"


# =============================================================================
# CI enforcement (workflow configuration)
# =============================================================================

def _workflow():
    return (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")


def _job(text, name):
    m = re.search(r"^  %s:\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)" % re.escape(name), text, re.M | re.S)
    assert m, f"job {name} missing"
    return m.group(1)


def test_ci_production_job_enforces_all_required_checks():
    job = _job(_workflow(), "verify-backend")
    for required in ('python-version-file: ".python-version"',
                     'pip install "./cardiovanta_ml[test]"',
                     "contracts/codegen/generate.py --check",
                     "scripts/verify_artifact_integrity.py",
                     "pip wheel ./cardiovanta_ml --no-deps",
                     "scripts/ci/verify_wheel_install.py",
                     "--model-id cardiovanta-lr13 --model-version 1.0.0",
                     'CARDIOVANTA_RUN_INSTALL_TESTS: "1"',
                     # CI data quarantine: tests run by explicit classification, never by directory
                     "pytest $(python scripts/ci/test_classification.py --list ci_safe)",
                     "CARDIOVANTA_DATA_QUARANTINE=1"):
        assert required in job, required
    assert "continue-on-error" not in job and "|| true" not in job
    assert not re.search(r"pytest\s+(tests|backend/tests)/?(\s|$)", job)  # no directory-wide collection
    # the backend synthetic suite, monitoring and artifact-integrity tests are all still in the ci_safe set
    spec = importlib.util.spec_from_file_location("ci_test_classification", ROOT / "scripts" / "ci" / "test_classification.py")
    tc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tc)
    safe = set(tc.ci_safe())
    assert {p.relative_to(ROOT).as_posix() for p in (ROOT / "backend" / "tests").glob("test_*.py")} <= safe
    assert {"tests/test_monitoring.py", "tests/test_artifact_integrity.py"} <= safe


def test_linux_build_workflow_is_pinned_and_never_deploys():
    raw = (ROOT / ".github" / "workflows" / "vercel-linux-build.yml").read_text(encoding="utf-8")
    text = "\n".join(line for line in raw.splitlines() if not line.lstrip().startswith("#"))
    assert 'VERCEL_CLI_VERSION: "59.26.0"' in text and 'vercel@${VERCEL_CLI_VERSION}' in text
    assert "npm install -g vercel\n" not in text and "vercel@latest" not in text
    assert "vercel pull --yes --environment=preview" in text and "vercel build --yes --target=preview" in text
    for forbidden in ("vercel deploy", "--prod", "--prebuilt", "vercel --yes"):
        assert forbidden not in text, forbidden
    assert "secrets.VERCEL_TOKEN" in text and "branches:\n      - main" not in text
    assert "rm -f .vercel/.env.*" in text  # pulled env files never uploaded
    assert (ROOT / "scripts" / "ci" / "inspect_vercel_bundle.py").is_file()


def test_deploy_job_pins_exact_vercel_cli_matching_linux_build():
    deploy = _job(_workflow(), "deploy")
    m = re.search(r'VERCEL_CLI_VERSION: "([^"]+)"', deploy)
    assert m and re.fullmatch(r"\d+\.\d+\.\d+", m.group(1)), "deploy must pin an exact x.y.z Vercel CLI"
    assert 'npm install -g "vercel@${VERCEL_CLI_VERSION}"' in deploy
    code = "\n".join(l for l in deploy.splitlines() if not l.lstrip().startswith("#"))
    assert not re.search(r"npm install -g vercel(\s|$)", code) and "vercel@latest" not in code
    assert not re.search(r"vercel@[\^~]", code)
    linux = (ROOT / ".github" / "workflows" / "vercel-linux-build.yml").read_text(encoding="utf-8")
    assert f'VERCEL_CLI_VERSION: "{m.group(1)}"' in linux, "deploy and Linux build workflows must use the same CLI"


def test_pull_requests_verify_without_deploying():
    text = _workflow()
    on = text.split("\npermissions:", 1)[0]
    assert re.search(r"pull_request:\n\s+branches:\n\s+- main", on), "PRs into main must run verification"
    assert re.search(r"push:\n\s+branches:\n\s+- main\n", on) and "pull_request_target" not in text
    for job in ("verify-backend", "quarantined-research-tests", "verify-frontend"):
        assert "\n    if:" not in "\n" + _job(text, job), f"{job} must run unconditionally (including on PRs)"
    deploy = _job(text, "deploy")
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in deploy
    assert "environment: production" in deploy
    assert "needs: [deploy]" in _job(text, "verify-production")      # skipped whenever deploy is skipped
    assert "--prod" not in text.replace(deploy, "")                 # production deploy only inside the gated job


def test_ci_research_suites_are_separate_and_frontend_checks_kept():
    text = _workflow()
    # The former broad `pytest tests/` research job read data/raw/heart.csv; it is replaced by a quarantined
    # job that runs only explicitly classified safe modules on the research (Python 3.11) stack.
    assert "research-data-tests:" not in text
    research = _job(text, "quarantined-research-tests")
    assert 'python-version: "3.11"' in research and "pip install -r requirements.txt" in research
    assert "pytest $(python scripts/ci/test_classification.py --list ci_safe --list ci_safe_research_deps)" in research
    assert not re.search(r"pytest\s+(tests|backend/tests)/?(\s|$)", research)
    frontend = _job(text, "verify-frontend")
    for step in ("npm ci", "npx tsc --noEmit", "npm run test", "npm run build"):
        assert step in frontend
    assert "needs: [verify-backend, quarantined-research-tests, verify-frontend]" in _job(text, "deploy")
    assert "continue-on-error" not in text
