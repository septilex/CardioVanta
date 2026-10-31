from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    MODEL_VERSION: str = "1.0.0"

    CORS_ORIGINS: List[str] = []
    ENABLE_DOCS: bool = False

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

settings = Settings()

