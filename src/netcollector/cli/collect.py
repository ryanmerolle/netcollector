"""Command to collect data from a source."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Annotated

import typer
from typer import rich_utils

from netcollector.cli.utils import (
    check_authentication_details,
    load_commands_with_cli_error_handling,
    load_config_with_cli_error_handling,
    load_inventory_with_cli_error_handling,
    version_callback,
)
from netcollector.collector.orchestrator import Collector
from netcollector.config.commands import CommandsByPlatform
from netcollector.config.config import Config
from netcollector.config.inventory import Inventory
from netcollector.config.utils import get_cwd_file
from netcollector.exceptions import InventoryLoadError
from netcollector.utils.database import DatabaseManager
from netcollector.utils.logging import AppLoggerAdapter, setup_logging

app = typer.Typer()


@app.callback()
@app.command()
def collect(  # pylint: disable=too-many-arguments,too-many-locals
    show_version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        rich_help_panel="Options",
        help="Print the version and exit",
    ),
    username: str = typer.Option(
        ...,
        "--user",
        "-u",
        rich_help_panel="Device Authentication",
        help="The username for devices authentication.",
        envvar="NETCOLLECTOR_USER",
    ),
    password: Annotated[
        str | None,
        typer.Option(
            ...,
            "--password",
            "-p",
            rich_help_panel="Device Authentication",
            help="The password for devices authentication.",
            envvar="NETCOLLECTOR_PASSWORD",
            hide_input=True,
        ),
    ] = None,
    auth_private_key: Annotated[
        Path | None,
        typer.Option(
            ...,
            "--private-key",
            "-pk",
            rich_help_panel="Device Authentication",
            help="Path to the private key used for authentication.",
            envvar="NETCOLLECTOR_AUTH_PRIVATE_KEY",
            dir_okay=False,
            exists=True,
            file_okay=True,
            resolve_path=True,
            readable=True,
        ),
    ] = None,
    private_key_passphrase: Annotated[
        str | None,
        typer.Option(
            ...,
            "--private-key-passphrase",
            "-pkp",
            rich_help_panel="Device Authentication",
            help="The passphrase for the private key used for authentication.",
            envvar="NETCOLLECTOR_PRIVATE_KEY_PASSPHRASE",
            hide_input=True,
        ),
    ] = None,
    inventory_file_path: Annotated[
        Path,
        typer.Option(
            ...,
            "--inventory-file",
            "-i",
            rich_help_panel="NetCollector Configuration",
            help="Path to the inventory file.",
            envvar="NETCOLLECTOR_INVENTORY_FILE",
            dir_okay=False,
            exists=True,
            file_okay=True,
            resolve_path=True,
            readable=True,
        ),
    ] = get_cwd_file("inventory.yaml"),
    config_file_path: Annotated[
        Path,
        typer.Option(
            ...,
            "--config-file",
            "-c",
            rich_help_panel="NetCollector Configuration",
            help="Path to the configuration file.",
            envvar="NETCOLLECTOR_CONFIG_FILE",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
        ),
    ] = get_cwd_file("netcollector.yaml"),
) -> None:
    """Collect data from a source."""
    auth_password, auth_private_key_passphrase = check_authentication_details(
        password, auth_private_key, private_key_passphrase
    )

    # Load inventory
    inventory: Inventory = load_inventory_with_cli_error_handling(
        inventory_file=inventory_file_path,
        default_user=username,
        default_password=auth_password,
        default_private_key=auth_private_key,
        default_private_key_passphrase=auth_private_key_passphrase,
    )
    _ = show_version
    # Load main configuration
    app_config: Config = load_config_with_cli_error_handling(config_file_path)

    # Setup logging as early as possible after config is loaded
    setup_logging(app_config.logging)

    # Get logger for this module after logging is configured
    base_logger = logging.getLogger(__name__)
    app_logger = AppLoggerAdapter(base_logger, operation="APPLICATION")

    app_logger.info("Logging configured successfully")

    # Load commands configuration from YAML file
    commands_by_platform: CommandsByPlatform = load_commands_with_cli_error_handling()

    if not inventory.devices:
        rich_utils.rich_format_error(
            InventoryLoadError("No devices found in the inventory. Nothing to do.")
        )
        raise typer.Abort()

    # Time the entire collection process
    collection_start_time = time.perf_counter()
    app_logger.info("Starting data collection...")

    # Create and initialize database manager
    with DatabaseManager(app_config.artifacts_path) as db_manager:
        try:
            db_path = db_manager.create_database()
            app_logger.info(f"Created collection database: {db_path.name}")
        except OSError as e:
            app_logger.error(f"Failed to create database: {e}")
            raise typer.Abort() from e

        collector = Collector()
        asyncio.run(
            collector.collect(
                device_configs=inventory.devices,
                commands_by_platform=commands_by_platform,
                output_dir=app_config.artifacts_path,
                db_manager=db_manager,
                max_concurrent_connections=app_config.max_concurrent_tasks,
            )
        )

    collection_time = time.perf_counter() - collection_start_time
    app_logger.info(
        f"Data collection complete - TotalTime: {collection_time:.1f}s, "
        f"Artifacts saved to: {app_config.artifacts_path}, "
        f"DuckDB Database: {db_path.name}"
    )


if __name__ == "__main__":
    app()
