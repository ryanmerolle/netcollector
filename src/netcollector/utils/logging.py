"""Structured logging utilities with context information.

This module provides custom LoggerAdapter classes that automatically inject
context information (like hostname, platform, command details) into log records
for better structured logging and debugging.
"""

import logging
import re
import sys
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

from netcollector.config.logging import LoggingConfig


class DeviceLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds device context to all log messages.

    Automatically injects hostname and platform information into log records
    to provide consistent device context across all related log messages.
    """

    def __init__(
        self,
        logger: logging.Logger,
        hostname: str,
        platform: str | None = None,
        task_descriptor: str = "DEVICE_PROCESSING",
    ) -> None:
        """Initialize the device logger adapter.

        Args:
            logger: The base logger to wrap.
            hostname: The hostname of the device.
            platform: The platform/OS type of the device.
            task_descriptor: The type of task being performed.

        """
        super().__init__(logger, {})
        self.hostname = hostname
        self.platform = platform or "unknown"
        self.task_descriptor = task_descriptor

    def _colorize_status(self, status: str) -> str:
        """Apply Rich color formatting to status messages.

        Args:
            status: The status string to colorize.

        Returns:
            The status string with Rich markup for coloring.

        """
        color_map = {
            "SUCCESS": "[bold green]SUCCESS[/bold green]",
            "STARTED": "[bold blue]STARTED[/bold blue]",
            "FAILED": "[bold red]FAILED[/bold red]",
            "SKIPPED": "[bold orange3]SKIPPED[/bold orange3]",
        }
        return color_map.get(status, status)

    def _format_message(self, msg: object, level_name: str | None = None) -> str:
        """Format message with consistent pattern."""
        status = level_name or "INFO"

        # Map logging levels to status names
        level_mapping = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "FAILED",
            "CRITICAL": "CRITICAL",
        }

        if status in level_mapping:
            status = level_mapping[status]

        # Check message content for status hints
        msg_str = str(msg).lower()
        if "success" in msg_str or "complete" in msg_str:
            status = "SUCCESS"
        elif "fail" in msg_str or "error" in msg_str:
            status = "FAILED"
        elif "skip" in msg_str:
            status = "SKIPPED"
        elif "starting" in msg_str or "start" in msg_str:
            status = "STARTED"
        elif msg_str == "" and self.task_descriptor == "DEVICE_PROCESSING":
            # Empty message for device processing indicates start
            status = "STARTED"

        # Apply Rich color formatting for status
        colored_status = self._colorize_status(status)

        # Format the message, only append the message part if there's content
        formatted = (
            f"{self.task_descriptor} - {colored_status} - "
            f"[purple]{self.hostname} ({self.platform})[/purple]"
        )
        if msg_str.strip():  # Only append message if there's actual content
            formatted += f" - {msg}"

        return formatted

    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        """Process the log message and add device context.

        Args:
            msg: The log message.
            kwargs: Keyword arguments for the log record.

        Returns:
            Tuple of processed message and updated kwargs with device context.

        """
        # Get level name from kwargs if available
        level_name = kwargs.get("extra", {}).get("level_name")

        formatted_msg = self._format_message(msg, level_name)

        extra = kwargs.setdefault("extra", {})
        extra.update(
            {
                "hostname": self.hostname,
                "platform": self.platform,
                "task_descriptor": self.task_descriptor,
                "device_context": f"{self.hostname}({self.platform})",
            }
        )
        return formatted_msg, kwargs


class CommandLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds command execution context to log messages.

    Provides detailed context about command execution including device info,
    command name, and the actual command being executed.
    """

    def __init__(
        self,
        logger: logging.Logger,
        hostname: str,
        platform: str | None = None,
        command_name: str | None = None,
        command_text: str | None = None,
    ) -> None:
        """Initialize the command logger adapter.

        Args:
            logger: The base logger to wrap.
            hostname: The hostname of the device.
            platform: The platform/OS type of the device.
            command_name: The logical name of the command.
            command_text: The actual command text being executed.

        """
        super().__init__(logger, {})
        self.hostname = hostname
        self.platform = platform or "unknown"
        self.command_name = command_name or "unknown_command"
        self.command_text = command_text or ""

    def _colorize_status(self, status: str) -> str:
        """Apply Rich color formatting to status messages.

        Args:
            status: The status string to colorize.

        Returns:
            The status string with Rich markup for coloring.

        """
        color_map = {
            "SUCCESS": "[bold green]SUCCESS[/bold green]",
            "STARTED": "[bold blue]STARTED[/bold blue]",
            "FAILED": "[bold red]FAILED[/bold red]",
            "SKIPPED": "[bold orange3]SKIPPED[/bold orange3]",
            "EXECUTING": "[bold cyan]EXECUTING[/bold cyan]",
        }
        return color_map.get(status, status)

    def _format_message(self, msg: object, level_name: str | None = None) -> str:
        """Format message with consistent pattern."""
        status = level_name or "INFO"

        # Map logging levels to status names
        level_mapping = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "FAILED",
            "CRITICAL": "CRITICAL",
        }

        if status in level_mapping:
            status = level_mapping[status]

        # Check message content for status hints
        msg_str = str(msg).lower()
        if "success" in msg_str or "complete" in msg_str:
            status = "SUCCESS"
        elif "fail" in msg_str or "error" in msg_str:
            status = "FAILED"
        elif "skip" in msg_str:
            status = "SKIPPED"
        elif "sending" in msg_str or "executing" in msg_str:
            status = "EXECUTING"
        elif "starting" in msg_str or "start" in msg_str:
            status = "STARTED"

        # Apply Rich color formatting for status
        colored_status = self._colorize_status(status)

        return (
            f"COMMAND_EXECUTION - {colored_status} - "
            f"[purple]{self.hostname}({self.platform})[/purple] - {msg}"
        )

    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        """Process the log message and add command execution context.

        Args:
            msg: The log message.
            kwargs: Keyword arguments for the log record.

        Returns:
            Tuple of processed message and updated kwargs with command context.

        """
        # Get level name from kwargs if available
        level_name = kwargs.get("extra", {}).get("level_name")

        formatted_msg = self._format_message(msg, level_name)

        extra = kwargs.setdefault("extra", {})
        extra.update(
            {
                "hostname": self.hostname,
                "platform": self.platform,
                "command_name": self.command_name,
                "command_text": self.command_text,
                "device_context": f"{self.hostname}({self.platform})",
                "command_context": f"{self.command_name}: {self.command_text}",
            }
        )
        return formatted_msg, kwargs


class AppLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for application-level messages.

    Provides consistent formatting for general application startup, shutdown,
    and other high-level operations.
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str = "APPLICATION",
        **context: str | int | float,
    ) -> None:
        """Initialize the app logger adapter.

        Args:
            logger: The base logger to wrap.
            operation: The type of operation (e.g., "APPLICATION", "STARTUP").
            **context: Additional context information as keyword arguments.

        """
        super().__init__(logger, {})
        self.operation = operation.upper()
        self.context = context

    def _colorize_status(self, status: str) -> str:
        """Apply Rich color formatting to status messages.

        Args:
            status: The status string to colorize.

        Returns:
            The status string with Rich markup for coloring.

        """
        color_map = {
            "SUCCESS": "[bold green]SUCCESS[/bold green]",
            "STARTED": "[bold blue]STARTED[/bold blue]",
            "FAILED": "[bold red]FAILED[/bold red]",
            "SKIPPED": "[bold orange3]SKIPPED[/bold orange3]",
        }
        return color_map.get(status, status)

    def _format_message(self, msg: object, level_name: str | None = None) -> str:
        """Format message with consistent pattern."""
        status = level_name or "INFO"

        # Map logging levels to status names
        level_mapping = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "FAILED",
            "CRITICAL": "CRITICAL",
        }

        if status in level_mapping:
            status = level_mapping[status]

        # Check message content for status hints
        msg_str = str(msg).lower()
        if "success" in msg_str or "complete" in msg_str:
            status = "SUCCESS"
        elif "fail" in msg_str or "error" in msg_str:
            status = "FAILED"
        elif "skip" in msg_str:
            status = "SKIPPED"
        elif "starting" in msg_str or "start" in msg_str:
            status = "STARTED"
        elif "configured" in msg_str and "success" in msg_str:
            status = "SUCCESS"

        # Apply Rich color formatting for status
        colored_status = self._colorize_status(status)

        return f"{self.operation} - {colored_status} - {msg}"

    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        """Process the log message and add application context.

        Args:
            msg: The log message.
            kwargs: Keyword arguments for the log record.

        Returns:
            Tuple of processed message and updated kwargs with app context.

        """
        # Get level name from kwargs if available
        level_name = kwargs.get("extra", {}).get("level_name")

        formatted_msg = self._format_message(msg, level_name)

        extra = kwargs.setdefault("extra", {})
        extra.update(
            {
                "operation": self.operation,
                **self.context,
            }
        )
        return formatted_msg, kwargs


class TimingLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds timing and performance context to log messages.

    Designed for logging performance metrics and timing information for
    various operations like device connections, command execution, parsing,
    and data export.
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation_type: str,
        **context: str | int | float,
    ) -> None:
        """Initialize the timing logger adapter.

        Args:
            logger: The base logger to wrap.
            operation_type: The type of operation being timed (e.g.,
                        "device_processing", "command_execution", "export").
            **context: Additional context information as keyword arguments.

        """
        super().__init__(logger, {})
        self.operation_type = operation_type.upper()
        self.context = context

    def _colorize_status(self, status: str) -> str:
        """Apply Rich color formatting to status messages.

        Args:
            status: The status string to colorize.

        Returns:
            The status string with Rich markup for coloring.

        """
        color_map = {
            "SUCCESS": "[bold green]SUCCESS[/bold green]",
            "STARTED": "[bold blue]STARTED[/bold blue]",
            "FAILED": "[bold red]FAILED[/bold red]",
            "SKIPPED": "[bold orange3]SKIPPED[/bold orange3]",
        }
        return color_map.get(status, status)

    def _format_message(self, msg: object, level_name: str | None = None) -> str:
        """Format message with consistent pattern."""
        status = level_name or "INFO"

        # Map logging levels to status names
        level_mapping = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "FAILED",
            "CRITICAL": "CRITICAL",
        }

        if status in level_mapping:
            status = level_mapping[status]

        # Check message content for status hints
        msg_str = str(msg).lower()
        if "success" in msg_str or "complete" in msg_str:
            status = "SUCCESS"
        elif "fail" in msg_str or "error" in msg_str:
            status = "FAILED"
        elif "skip" in msg_str:
            status = "SKIPPED"
        elif "starting" in msg_str or "start" in msg_str:
            status = "STARTED"
        elif status == "INFO" and ("time:" in msg_str or "records:" in msg_str):
            # Timing messages with metrics indicate successful completion
            status = "SUCCESS"

        # Get hostname and platform from context
        hostname = self.context.get("hostname", "unknown")
        platform = self.context.get("platform", "unknown")

        # Apply Rich color formatting for status
        colored_status = self._colorize_status(status)

        return (
            f"{self.operation_type} - {colored_status} - "
            f"[purple]{hostname} ({platform})[/purple] - {msg}"
        )

    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        """Process the log message and add timing context.

        Args:
            msg: The log message.
            kwargs: Keyword arguments for the log record.

        Returns:
            Tuple of processed message and updated kwargs with timing context.

        """
        # Get level name from kwargs if available
        level_name = kwargs.get("extra", {}).get("level_name")

        formatted_msg = self._format_message(msg, level_name)

        extra = kwargs.setdefault("extra", {})
        extra.update(
            {
                "operation_type": self.operation_type,
                **self.context,
            }
        )
        return formatted_msg, kwargs


def _strip_rich_markup(text: str) -> str:
    """Remove Rich markup from text for clean file logging.

    Args:
        text: Text containing Rich markup.

    Returns:
        Text with Rich markup removed.

    """
    # Remove Rich markup tags like [bold green], [/bold green], [purple], etc.
    return re.sub(r"\[/?[^\]]*\]", "", text)


class PlainTextFormatter(logging.Formatter):
    """Custom formatter that strips Rich markup for file logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record and strip Rich markup."""
        formatted = super().format(record)
        return _strip_rich_markup(formatted)


def setup_logging(config: LoggingConfig) -> None:
    """Configure logging for the application using Rich.

    This function configures logging for the entire application, setting up
    Rich handlers with proper formatting and log levels for different modules.
    Additionally configures file logging if a valid logfile path is provided.

    Args:
        config: LoggingConfig instance containing logging configuration.

    """
    # Remove any existing handlers to start fresh
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create Rich console handler for stdout/stderr if enabled
    if config.main.stdout:
        console = Console(
            file=sys.stderr,
            force_terminal=True,
        )

        rich_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
            show_time=True,
            show_level=True,
            show_path=False,  # Disable path to reduce clutter
        )

        root_logger.addHandler(rich_handler)

    # Create file handler if logfile path is configured
    if config.main.logfile is not None:
        try:
            # Ensure the directory exists
            logfile_path = Path(config.main.logfile)
            logfile_path.parent.mkdir(parents=True, exist_ok=True)

            # Create file handler with rotation support
            file_handler = logging.FileHandler(
                filename=logfile_path, mode="a", encoding="utf-8"
            )

            # Set a more detailed format for file logging with markup removal
            file_formatter = PlainTextFormatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(getattr(logging, config.main.level.upper()))

            root_logger.addHandler(file_handler)

        except (OSError, PermissionError) as e:
            # If file logging fails, log a warning but continue with console logging
            if config.main.stdout:
                logging.warning("Failed to setup file logging: %s", e)

    # Configure root logger
    root_logger.setLevel(logging.DEBUG)

    # Configure application-specific loggers
    _configure_logger("netcollector", config.main.level)
    _configure_logger("scrapli", config.scrapli.level)
    _configure_logger("pandas", config.pandas.level)

    # Suppress noisy third-party loggers
    _suppress_noisy_loggers()


def _configure_logger(logger_name: str, level: str) -> None:
    """Configure a specific logger with the given level.

    Args:
        logger_name: Name of the logger to configure.
        level: Log level as a string (e.g., "INFO", "DEBUG").

    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))


def _suppress_noisy_loggers() -> None:
    """Suppress logging from noisy third-party libraries."""
    # Common noisy loggers that should be quieted
    noisy_loggers = [
        "urllib3.connectionpool",
        "asyncio",
        "concurrent.futures",
        "asyncssh",
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    This is a convenience function that ensures consistent logger naming
    across the application.

    Args:
        name: Name for the logger, typically __name__.

    Returns:
        Configured logger instance.

    """
    return logging.getLogger(name)
