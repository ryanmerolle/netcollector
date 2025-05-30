"""CLI utility functions."""

import importlib.metadata
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import typer
from pydantic import SecretStr
from rich import print as rich_print
from typer import Exit as typerExit
from typer import rich_utils

from netcollector.config.commands import CommandsByPlatform, load_commands
from netcollector.config.config import Config, load_config
from netcollector.config.inventory import Inventory, load_inventory
from netcollector.exceptions import (
    ConfigLoadError,
    ContradictingOptionsError,
    InventoryLoadError,
    MissingOptionsError,
)


def cli_error_handler(
    error_class: type[Exception] = ConfigLoadError,
    error_message_prefix: str = "Error loading",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator to standardize CLI error handling for loader functions.

    Args:
        error_class: The exception class to use for error formatting.
        error_message_prefix: The prefix for error messages.

    Returns:
        A decorator that wraps functions with standardized CLI error handling.

    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:  # type: ignore[misc] # noqa: ANN002,ANN003,ANN401
            try:
                result = func(*args, **kwargs)
                if result is None:
                    rich_utils.rich_format_error(
                        error_class(f"Failed to load using {func.__name__}.")
                    )
                    raise typer.Abort()
                return result
            except Exception as exc:
                rich_utils.rich_format_error(
                    error_class(f"{error_message_prefix}: {exc}")
                )
                raise typer.Abort() from exc

        return wrapper

    return decorator


# https://github.com/fastapi/typer/issues/52
def version_callback(value: bool) -> None:
    """Display the version of the CLI."""
    if value:
        package_version = importlib.metadata.version("netcollector")
        rich_print(f"NetCollector {package_version}")
        raise typerExit(0)


def check_authentication_details(
    password: str | None,
    private_key: Path | None,
    private_key_passphrase: str | None,
) -> tuple[SecretStr | None, SecretStr | None]:
    """Check if authentication parameters are provided.

    Args:
        password: The password for authentication.
        private_key: Path to the private key file.
        private_key_passphrase: The passphrase for the private key.

    Returns:
        A tuple containing the processed password and private key passphrase as
        SecretStr objects.

    Raises:
        typer.Abort: If authentication parameters are invalid or contradictory.

    """
    if password:
        auth_password = SecretStr(password)
    else:
        auth_password = None

    if private_key_passphrase:
        auth_private_key_passphrase = SecretStr(private_key_passphrase)
    else:
        auth_private_key_passphrase = None

    if private_key is None and auth_password is None:
        rich_utils.rich_format_error(
            MissingOptionsError(
                "Either '--password' / '-p' or '--private-key' / '-pk' is required."
            )
        )
        raise typer.Abort()

    if auth_password is not None and private_key is not None:
        rich_utils.rich_format_error(
            ContradictingOptionsError(
                "Contradicting options by setting both '--password' / '-p'"
                " and '--private-key' / '-pk'."
            )
        )
        raise typer.Abort()

    if auth_private_key_passphrase and private_key is None:
        rich_utils.rich_format_error(
            MissingOptionsError(
                "When setting '--private-key-passphrase' / '-pkp' a "
                "'--private-key' / '-pk' is required."
            )
        )
        raise typer.Abort()

    return (
        auth_password,
        auth_private_key_passphrase,
    )


@cli_error_handler(InventoryLoadError, "Error loading inventory")
def load_inventory_with_cli_error_handling(
    inventory_file: Path,
    default_user: str,
    default_password: SecretStr | None,
    default_private_key: Path | None,
    default_private_key_passphrase: SecretStr | None,
) -> Inventory:
    """Load inventory from a YAML file with CLI error handling.

    Args:
        inventory_file: Path to the inventory file.
        default_user: Default username for devices.
        default_password: Default password for devices.
        default_private_key: Default private key path for devices.
        default_private_key_passphrase: Default private key passphrase for devices.

    Returns:
        The loaded inventory configuration.

    Raises:
        typer.Abort: If the inventory cannot be loaded.

    """
    inventory = load_inventory(
        inventory_file,
        default_user,
        default_password,
        default_private_key,
        default_private_key_passphrase,
    )
    return inventory


@cli_error_handler(ConfigLoadError, "Error loading configuration")
def load_config_with_cli_error_handling(config_file_path: Path | None) -> Config:
    """Load configuration from a YAML file with CLI error handling.

    Args:
        config_file_path: Path to the configuration file.

    Returns:
        The loaded configuration.

    Raises:
        typer.Abort: If the configuration cannot be loaded.

    """
    config = load_config(config_file_path)
    return config


@cli_error_handler(ConfigLoadError, "Error loading commands")
def load_commands_with_cli_error_handling(
    commands_file_path: Path | None = None,
) -> CommandsByPlatform:
    """Load commands configuration from a YAML file with CLI error handling.

    Args:
        commands_file_path: Path to the commands file.

    Returns:
        The loaded commands configuration.

    Raises:
        typer.Abort: If the commands cannot be loaded.

    """
    commands = load_commands(commands_file_path)
    return commands
