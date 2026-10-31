"""
SHA-256 integrity verification for registered model artifacts.

What this guarantees
--------------------
* Every artifact the registry will deserialize is byte-identical to the file
  recorded in the model's checksum manifest (``checksums.sha256``) when the model
  was registered.
* The manifest itself matches the SHA-256 recorded in the registry metadata, so
  editing the manifest alone (for example after swapping an artifact) is detected.
* All paths resolve inside the declared directories. Absolute paths, ``..``
  segments, separators in file names and symlinks escaping the directory are
  rejected.
* Verification happens BEFORE any artifact is deserialized.

What it does NOT guarantee
--------------------------
The manifest and metadata are unsigned files in the same repository. Someone who
can change an artifact and also update the manifest and metadata consistently will
not be detected. These checks detect accidental or partial modification,
corruption and drift relative to the registered manifest. They are not
cryptographic proof of authenticity or provenance (that would need signatures
or an external trusted record).
"""
import hashlib
import hmac
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, Iterable

from cardiovanta_ml.registry.exceptions import ArtifactPathError, IntegrityError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_LINE_RE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sha256_file(path: Path, chunk_size: int = 1 << 16) -> str:
    """Streaming SHA-256 of a file's raw bytes."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.match(value) is not None


def validate_file_name(name: object) -> str:
    """Accept only a plain file name (no directories, no traversal, no absolute paths)."""
    if not isinstance(name, str) or not name:
        raise ArtifactPathError(f"Artifact file name must be a non-empty string, got {name!r}")
    if PurePosixPath(name).name != name or PureWindowsPath(name).name != name or not _SAFE_NAME_RE.match(name):
        raise ArtifactPathError(f"Unsafe artifact file name {name!r}: only plain file names are allowed")
    return name


def resolve_within(base: Path, relative: object) -> Path:
    """
    Resolve ``relative`` against ``base`` and require the result to stay inside ``base``.

    Rejects absolute paths, drive letters, ``..`` segments, and symlinks resolving outside ``base``.
    """
    if not isinstance(relative, str) or not relative:
        raise ArtifactPathError(f"Path must be a non-empty relative string, got {relative!r}")
    posix, windows = PurePosixPath(relative), PureWindowsPath(relative)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or "\\" in relative:
        raise ArtifactPathError(f"Absolute or non-POSIX path not allowed: {relative!r}")
    if any(part in ("..", ".") for part in posix.parts) or not posix.parts:
        raise ArtifactPathError(f"Path traversal not allowed: {relative!r}")
    base_resolved = base.resolve()
    target = (base_resolved / Path(*posix.parts)).resolve()
    if target != base_resolved and base_resolved not in target.parents:
        raise ArtifactPathError(f"Path {relative!r} resolves outside {base_resolved}")
    return target


def parse_checksum_manifest(text: str) -> Dict[str, str]:
    """
    Parse a ``sha256sum``-format manifest: ``<64 lowercase hex>  <file name>`` per line.

    Blank lines and ``#`` comments are ignored. Duplicates and malformed lines are rejected.
    """
    entries: Dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _MANIFEST_LINE_RE.match(line)
        if not match:
            raise IntegrityError(f"Malformed checksum manifest line {lineno}: {raw!r}")
        digest, name = match.group(1), validate_file_name(match.group(2).strip())
        if name in entries:
            raise IntegrityError(f"Duplicate checksum manifest entry for {name!r}")
        entries[name] = digest
    if not entries:
        raise IntegrityError("Checksum manifest is empty")
    return entries


def verify_manifest_file(manifest_path: Path, expected_sha256: str) -> Dict[str, str]:
    """Check the manifest's own hash against the registry metadata, then parse it."""
    if not manifest_path.is_file():
        raise IntegrityError(f"Checksum manifest not found: {manifest_path.name}")
    actual = sha256_file(manifest_path)
    if not hmac.compare_digest(actual, expected_sha256):
        raise IntegrityError(
            f"Checksum manifest {manifest_path.name} does not match the SHA-256 recorded in registry metadata"
        )
    return parse_checksum_manifest(manifest_path.read_text(encoding="utf-8"))


def verify_artifacts(artifact_dir: Path, manifest: Dict[str, str], declared_files: Iterable[str]) -> Dict[str, Path]:
    """
    Verify that the manifest covers exactly the declared artifacts and every file matches its hash.

    Returns ``{file name: resolved path}``. Raises ``IntegrityError`` before anything is deserialized.
    """
    declared = {validate_file_name(name) for name in declared_files}
    missing_from_manifest = declared - set(manifest)
    unexpected_in_manifest = set(manifest) - declared
    if missing_from_manifest:
        raise IntegrityError(f"Artifacts missing from checksum manifest: {sorted(missing_from_manifest)}")
    if unexpected_in_manifest:
        raise IntegrityError(f"Unexpected artifacts in checksum manifest: {sorted(unexpected_in_manifest)}")

    verified: Dict[str, Path] = {}
    for name in sorted(declared):
        path = resolve_within(artifact_dir, name)
        if not path.is_file():
            raise IntegrityError(f"Required artifact not found: {name}")
        actual = sha256_file(path)
        if not hmac.compare_digest(actual, manifest[name]):
            raise IntegrityError(f"SHA-256 mismatch for artifact {name}: refusing to load")
        verified[name] = path
    return verified
