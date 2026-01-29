"""Configuration-specific exception classes."""

from ..core.exceptions import ConfigurationError


class ConfigLoadError(ConfigurationError):
    """Exception raised when configuration cannot be loaded."""
    pass


class ConfigSaveError(ConfigurationError):
    """Exception raised when configuration cannot be saved."""
    pass


class ConfigValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""
    pass