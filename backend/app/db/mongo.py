"""
MongoDB store for anonymous explanation feedback (openspec/changes/explanation-feedback-mongodb).

``MONGODB_URI`` comes only from ``settings.require_secret`` and is never logged. ``pymongo`` is imported lazily,
so prediction serving never loads it. One ``MongoClient`` is kept per process: it is thread-safe and reused across
warm serverless invocations. Documents hold no personal or clinical data.
"""
import hashlib
import hmac
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from backend.app.core.config import Settings, settings as default_settings

COLLECTION = "explanation_feedback"
DEFAULT_DATABASE = "cardiovanta"
TIMEOUT_MS = 3000
SECTION_INDEX = "feedback_section_1"

_clients: Dict[str, Any] = {}
_lock = threading.Lock()


class FeedbackStoreUnavailable(RuntimeError):
    """MongoDB could not be reached. The message never contains the connection string."""


def _client(uri: str) -> Any:
    import pymongo  # lazy: only the feedback endpoints need the driver

    with _lock:
        client = _clients.get(uri)
        if client is None:
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=TIMEOUT_MS, connectTimeoutMS=TIMEOUT_MS,
                                         socketTimeoutMS=TIMEOUT_MS, appname="cardiovanta-feedback", tz_aware=True)
            _clients[uri] = client
        return client


def collection(cfg: Optional[Settings] = None) -> Any:
    """The feedback collection. Raises MissingSecretError when MONGODB_URI is not configured."""
    uri = (cfg or default_settings).require_secret("MONGODB_URI")
    client = _client(uri)
    db = client.get_default_database(default=DEFAULT_DATABASE)
    col = db[COLLECTION]
    # MongoDB create_index is idempotent for an existing key/options pair. Running it
    # from the lazy accessor keeps every warm or cold process on the same schema.
    from pymongo import ASCENDING

    col.create_index([("section", ASCENDING)], name=SECTION_INDEX)
    return col


def reset_clients() -> None:
    """Close cached clients (tests)."""
    with _lock:
        for client in _clients.values():
            client.close()
        _clients.clear()


# --- edit tokens ------------------------------------------------------------------------------------------

def new_edit_token() -> Tuple[str, str]:
    """A one-time token for the person who created the feedback, and the SHA-256 that is stored instead."""
    token = secrets.token_urlsafe(24)
    return token, token_hash(token)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(token_hash(token), stored_hash)


def now() -> datetime:
    return datetime.now(timezone.utc)


def public_view(doc: Dict[str, Any]) -> Dict[str, Any]:
    """What the API returns for a document: never the token hash."""
    return {
        "id": str(doc["_id"]),
        "helpful": doc["helpful"],
        "section": doc["section"],
        "model_version": doc["model_version"],
        "created_at": doc["created_at"].isoformat(),
        "updated_at": doc["updated_at"].isoformat(),
    }
