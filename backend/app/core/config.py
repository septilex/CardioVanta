"""
Application settings, read from environment variables (and a local, gitignored ``.env`` in development).

Configuration vs secrets:
- Configuration (model ID/version, CORS origins, docs switch) is not sensitive. ``.env.example`` documents it
  with example values.
- Secrets (database connection strings with embedded passwords) are typed as ``SecretStr``. Their value is
  masked as ``**********`` in ``repr``, ``str``, logs and ``model_dump()``; code must call
  ``require_secret(...)`` to read the real value, which is the only place it is exposed. ``.env.example``
  lists their names with empty values, real values live in ``.env`` locally and in the Vercel project's
  environment settings in production, never in the repository or the browser bundle (no ``NEXT_PUBLIC_``).

``python -m backend.app.core.config`` prints which settings are configured without printing any secret.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Settings whose values must never be printed, logged or sent to the browser.
SECRET_SETTINGS = ("DATABASE_URL", "MONGODB_URI")


class MissingSecretError(RuntimeError):
    """A feature needs a secret that is not configured. The message names the variable, never a value."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "CardioVanta"
    ENVIRONMENT: str = "production"
    # Project root is 4 levels up from this file (backend/app/core/config.py -> core -> app -> backend -> root)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    MODEL_DIR: Path = BASE_DIR / "artifacts" / "model"

    # Versioned model registry (R2). The served model is selected EXPLICITLY by ID and
    # exact version; the registry never picks a "latest" version. Override via env vars
    # MODEL_ID / MODEL_VERSION / MODEL_REGISTRY_ROOT (absolute path).
    MODEL_REGISTRY_ROOT: Path = BASE_DIR / "artifacts"
    MODEL_ID: str = "cardiovanta-lr13"
    MODEL_VERSION: str = "1.1.1"

    CORS_ORIGINS: List[str] = []
    ENABLE_DOCS: bool = False

    # Secrets. Optional: prediction serving needs neither, so the app starts without them; only the features
    # that use a database read them, through require_secret().
    DATABASE_URL: Optional[SecretStr] = None   # PostgreSQL, e.g. postgresql://user:password@host:5432/db
    MONGODB_URI: Optional[SecretStr] = None    # MongoDB, e.g. mongodb+srv://user:password@cluster/db

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator(*SECRET_SETTINGS, mode="before")
    @classmethod
    def blank_secret_is_unset(cls, v: object) -> object:
        # `DATABASE_URL=` in .env (as copied from .env.example) means "not configured", not "empty password".
        if isinstance(v, str) and not v.strip():
            return None
        return v

    def require_secret(self, name: str) -> str:
        """The real value of a configured secret, for the code that opens the connection.

        Raises MissingSecretError naming the variable (never a value) when it is not configured.
        """
        if name not in SECRET_SETTINGS:
            raise KeyError(f"{name} is not a secret setting")
        secret: Optional[SecretStr] = getattr(self, name)
        if secret is None:
            raise MissingSecretError(
                f"{name} is not configured. Set it in .env for local development or in the Vercel project's "
                f"environment variables for deployments (see .env.example)."
            )
        return secret.get_secret_value()

    def configuration_report(self) -> Dict[str, str]:
        """Which settings are configured, safe to print: secrets show only 'set' or 'not set'."""
        report = {
            "ENVIRONMENT": self.ENVIRONMENT,
            "MODEL_ID": self.MODEL_ID,
            "MODEL_VERSION": self.MODEL_VERSION,
            "CORS_ORIGINS": f"{len(self.CORS_ORIGINS)} origin(s)",
            "ENABLE_DOCS": str(self.ENABLE_DOCS),
        }
        for name in SECRET_SETTINGS:
            report[name] = "set" if getattr(self, name) is not None else "not set"
        return report


settings = Settings()


if __name__ == "__main__":
    for key, value in settings.configuration_report().items():
        print(f"{key:15s} {value}")
    sys.exit(0)
