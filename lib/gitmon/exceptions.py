"""Custom exceptions for gitmon."""


class GitMonError(Exception):
    """Base exception for all gitmon errors."""


class ConfigurationError(GitMonError):
    """Raised when there is an error in configuration."""


class GitCommandError(GitMonError):
    """Raised when a git command fails."""
