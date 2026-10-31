"""Structured registry exceptions. All derive from ``RegistryError``; every one means "do not serve"."""


class RegistryError(Exception):
    """Base class: the requested model must not be served."""


class RegistryConfigurationError(RegistryError):
    """The registry root is missing or not an explicit absolute path."""


class ModelNotRegisteredError(RegistryError):
    """Unknown or malformed model ID/version (there is no 'latest' fallback)."""


class MetadataError(RegistryError):
    """Registry metadata is missing, malformed, contradictory or incomplete."""


class IntegrityError(RegistryError):
    """An artifact is missing, unexpected, or does not match its registered SHA-256."""


class ArtifactPathError(IntegrityError):
    """An artifact path is absolute, traverses outside its directory, or is otherwise unsafe."""


class ContractMismatchError(RegistryError):
    """The model was registered against a different clinical feature contract."""


class OutcomeMappingError(RegistryError):
    """The model's class-label to clinical-outcome mapping is missing, ambiguous or contradictory."""


class ModelCompatibilityError(RegistryError):
    """The deserialized model does not match its metadata (classes, features, runtime, association)."""
