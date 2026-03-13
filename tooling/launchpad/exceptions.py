"""
Custom exceptions for Launchpad.
"""


class LaunchpadException(Exception):
    """Base exception for all Launchpad errors."""


class ConfigurationError(LaunchpadException):
    """Raised when configuration is invalid or missing."""


class KubernetesError(LaunchpadException):
    """Raised when Kubernetes operations fail."""


class CommandNotFoundError(LaunchpadException):
    """Raised when a required command is not found."""


class PasswordError(LaunchpadException):
    """Raised when password operations fail."""


class ManifestError(LaunchpadException):
    """Raised when manifest operations fail."""
