"""Exceptions for the NetCollector."""

import click


class NetCollectorCliError(click.ClickException):
    """Base exception for NetCollector CLI errors."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        """Initialize the NetCollectorCliError with a message and exit code.

        Args:
            message: The error message to display.
            exit_code: The exit code to use when the exception is raised.

        """
        super().__init__(message)
        self.exit_code = exit_code


class ContradictingOptionsError(NetCollectorCliError):
    """Custom exception for contradicting CLI options."""


class MissingOptionsError(NetCollectorCliError):
    """Custom exception for missing CLI options."""


class InventoryLoadError(NetCollectorCliError):
    """Custom exception for inventory loading failures."""


class ConfigLoadError(NetCollectorCliError):
    """Custom exception for inventory loading failures."""
