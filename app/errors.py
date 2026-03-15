"""Application-specific exceptions."""


class AppError(Exception):
    """Base class for user-facing application errors."""


class ConfigError(ValueError):
    """Raised when config parsing fails."""


class OutputError(AppError):
    """Raised when output file writing fails."""


class RenderError(AppError):
    """Raised when rendering fails."""
