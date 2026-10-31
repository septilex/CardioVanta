"""
Package configuration.

The package never guesses where models live and never infers paths from the
current working directory. A registry root must be passed explicitly, or be set
through the ``CARDIOVANTA_MODEL_REGISTRY`` environment variable.

There is deliberately no "default" or "latest" model: callers must name an
explicit model ID and version.
"""
import os
from pathlib import Path
from typing import Optional, Union

REGISTRY_ROOT_ENV = "CARDIOVANTA_MODEL_REGISTRY"

# Registry layout below the registry root: <root>/models/<model_id>/<model_version>/
MODELS_SUBDIR = "models"
REGISTRY_METADATA_FILE = "metadata.json"
REGISTRY_SCHEMA_VERSION = "1.0"


def resolve_registry_root(registry_root: Optional[Union[str, Path]] = None) -> Path:
    """Return the explicit registry root, or the one from ``CARDIOVANTA_MODEL_REGISTRY``."""
    if registry_root is None:
        env = os.environ.get(REGISTRY_ROOT_ENV)
        if not env:
            from cardiovanta_ml.registry.exceptions import RegistryConfigurationError

            raise RegistryConfigurationError(
                f"No model registry root given and {REGISTRY_ROOT_ENV} is not set."
            )
        registry_root = env
    root = Path(registry_root)
    if not root.is_absolute():
        from cardiovanta_ml.registry.exceptions import RegistryConfigurationError

        raise RegistryConfigurationError(
            f"Model registry root must be an absolute path (got {str(registry_root)!r}); "
            "relative paths would depend on the working directory."
        )
    return root.resolve()
