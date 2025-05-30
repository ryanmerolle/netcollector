"""Orchestration and workflow logic for network data collection.

This module contains the core business logic for orchestrating data collection
from network devices, including connection management, command execution,
and data processing workflows.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from scrapli import AsyncScrapli

from netcollector.collector.factories import ParserFactory
from netcollector.collector.interfaces import IOutputParser, ParsedData
from netcollector.collector.normalizer import DataNormalizer
from netcollector.config.commands import CommandDetail, CommandsByPlatform
from netcollector.config.inventory import Device
from netcollector.utils.database import DatabaseManager
from netcollector.utils.logging import (
    AppLoggerAdapter,
    CommandLoggerAdapter,
    DeviceLoggerAdapter,
    TimingLoggerAdapter,
)
from netcollector.utils.storage import DataStorageService

# Type Aliases for stricter typing
type CommandsDict = dict[str, CommandDetail]


def _get_ssh_config_file(device_config: Device) -> str:
    """Determine the SSH config file path."""
    if (
        device_config.auth_private_key
        and hasattr(device_config, "ssh_config_file")
        and device_config.ssh_config_file is True
    ):  # type: ignore[attr-defined]
        return str(device_config.auth_private_key.parent / "config")
    return "~/.ssh/config"


async def _send_commands_to_device(
    conn: AsyncScrapli,
    hostname: str,
    platform: str,
    commands_to_run: CommandsDict,
    parser: IOutputParser,
) -> list[tuple[str, ParsedData]]:
    """Send commands to a device and parse the output."""
    base_logger = logging.getLogger(__name__)
    results_per_command: list[tuple[str, ParsedData]] = []

    for command_name, cmd_detail in commands_to_run.items():
        command_to_send = cmd_detail.command

        # Create command-specific logger adapter
        command_logger = CommandLoggerAdapter(
            base_logger,
            hostname=hostname,
            platform=platform,
            command_name=command_name,
            command_text=command_to_send,
        )

        if not command_to_send:
            command_logger.warning(
                f"Skipping command '{command_name}': No command string provided"
            )
            results_per_command.append((command_name, []))
            continue

        # Time command execution
        command_start_time = time.perf_counter()
        command_logger.debug(f"Sending command '{command_to_send}'")
        response = await conn.send_command(command_to_send)
        command_execution_time = time.perf_counter() - command_start_time

        if response.failed:
            command_logger.error(
                f"Command '{command_name}' failed after {command_execution_time:.1f}s: "
                f"{response.scrapli_response.error}"
            )
            results_per_command.append((command_name, []))
            continue

        # Time parsing
        parsing_start_time = time.perf_counter()
        parsed_output = parser.parse(response, hostname, platform)
        parsing_time = time.perf_counter() - parsing_start_time

        # Time normalization
        normalization_start_time = time.perf_counter()
        normalizer = DataNormalizer()
        normalized_output = normalizer.normalize(
            parsed_output, cmd_detail, hostname, platform, command_name
        )
        normalization_time = time.perf_counter() - normalization_start_time

        # Add metadata to each record
        for record in normalized_output:
            record["hostname"] = hostname
            record["command_name"] = command_name
        results_per_command.append((command_name, normalized_output))

        # Log completion with timing and structured context
        timing_logger = TimingLoggerAdapter(
            base_logger,
            operation_type="command_execution",
            hostname=hostname,
            platform=platform,
            command_name=command_name,
            execution_time=round(command_execution_time, 3),
            parsing_time=round(parsing_time, 3),
            normalization_time=round(normalization_time, 3),
            records_parsed=len(parsed_output),
            records_normalized=len(normalized_output),
        )
        timing_logger.debug(
            f"Command '{command_name}' completed - "
            f"Execution: {command_execution_time:.1f}s, "
            f"Parsing: {parsing_time:.1f}s, "
            f"Normalization: {normalization_time:.1f}s, "
            f"Records: {len(parsed_output)} -> {len(normalized_output)}"
        )
    return results_per_command


async def process_device_task(
    device_config: Device,
    commands_to_run: CommandsDict,
    parser: IOutputParser,
) -> list[tuple[str, ParsedData]]:
    """Process commands on a single network device.

    Connects to the device, sends commands, parses output, and augments data.

    Args:
        device_config: Device connection details (host, platform, auth).
        commands_to_run: Dictionary of command names to CommandDetail objects
                        to execute.
        parser: IOutputParser instance for parsing.

    Returns:
        List of (command_name, parsed_data_list) tuples. Empty on critical failure.

    """
    base_logger = logging.getLogger(__name__)
    hostname: str = device_config.hostname
    platform: str | None = device_config.platform
    results_per_command: list[tuple[str, ParsedData]] = []

    # Create device-specific logger
    device_logger = DeviceLoggerAdapter(
        base_logger,
        hostname=hostname,
        platform=platform,
        task_descriptor="DEVICE_CONNECTION",
    )

    if not platform:
        device_logger.warning("Platform not specified")
        return results_per_command

    auth_password_for_scrapli: str | None = None
    if device_config.auth_password:
        auth_password_for_scrapli = device_config.auth_password.get_secret_value()

    conn_params: dict[str, Any] = {
        "host": device_config.host,
        "platform": platform,
        "auth_username": device_config.auth_username,
        "auth_password": auth_password_for_scrapli,
        "auth_strict_key": device_config.auth_strict_key,
        "transport": device_config.transport,
    }

    if conn_params["transport"] in ("asyncssh", "ssh", "systemssh"):
        conn_params["ssh_config_file"] = _get_ssh_config_file(device_config)

    if device_config.port is not None:
        conn_params["port"] = device_config.port

    if not conn_params.get("host"):
        device_logger.warning("Host not specified")
        return results_per_command

    # Time overall device processing
    device_start_time = time.perf_counter()

    try:
        # Time connection establishment
        connection_start_time = time.perf_counter()
        async with AsyncScrapli(**conn_params) as conn:
            connection_time = time.perf_counter() - connection_start_time
            device_logger.debug(f"Successfully connected in {connection_time:.1f}s")

            # Time command execution phase
            commands_start_time = time.perf_counter()
            results_per_command = await _send_commands_to_device(
                conn, hostname, platform, commands_to_run, parser
            )
            commands_time = time.perf_counter() - commands_start_time

            # Log overall device processing timing
            total_device_time = time.perf_counter() - device_start_time
            timing_logger = TimingLoggerAdapter(
                base_logger,
                operation_type="device_processing",
                hostname=hostname,
                platform=platform,
                connection_time=round(connection_time, 3),
                commands_time=round(commands_time, 3),
                total_time=round(total_device_time, 3),
                commands_count=len(commands_to_run),
                records_collected=sum(len(data) for _, data in results_per_command),
            )
            timing_logger.info(
                f"ConnectionTime: {connection_time:.1f}s, "
                f"CommandsTime: {commands_time:.1f}s, "
                f"TotalTime: {total_device_time:.1f}s, "
                f"Records: {sum(len(data) for _, data in results_per_command)}"
            )

    except ImportError:
        device_logger.error("Scrapli or transport library not installed correctly")
        return []
    except OSError as e:
        device_logger.error(f"Network error: {e!r}")
        return results_per_command  # Return any partial results
    except Exception as e:
        device_logger.error(f"Unexpected error: {e!r}")
        return results_per_command  # Return any partial results

    return results_per_command


async def main_workflow(
    device_configs: list[Device],
    commands_by_platform: CommandsByPlatform,
    max_concurrent_connections: int,
    output_dir: Path,
    parser: IOutputParser,
    db_manager: DatabaseManager,
) -> None:
    """Orchestrate data collection, parsing, and exporting for multiple devices.

    Args:
        device_configs: List of device configuration dictionaries.
        commands_by_platform: Maps platform to list of command dicts.
        max_concurrent_connections: Max concurrent device connections.
        output_dir: Base directory for saved data.
        parser: Parser instance for processing command output.
        db_manager: Database manager for DuckDB operations.

    """
    logger = logging.getLogger(__name__)
    semaphore = asyncio.Semaphore(max_concurrent_connections)

    # Create data storage service
    storage_service = DataStorageService(db_manager)

    tasks = []

    async def guarded_task(device_info: Device) -> None:
        async with semaphore:
            platform = device_info.platform
            device_logger = DeviceLoggerAdapter(
                logger,
                hostname=device_info.hostname,
                platform=platform,
                task_descriptor="DEVICE_PROCESSING",
            )

            if not platform:
                device_logger.warning("No platform defined - skipping device")
                return

            cmds_for_platform = commands_by_platform.get(platform)
            if not cmds_for_platform:
                device_logger.warning(
                    "No commands defined for this platform - skipping device"
                )
                return

            device_logger.info("")
            command_results = await process_device_task(
                device_info, cmds_for_platform, parser
            )

            for command_name, data_list in command_results:
                if data_list:
                    # TODO: Uncomment export functionality when ready
                    device_logger.debug(
                        f"Command '{command_name}' collected {len(data_list)} records -"
                        f" export functionality temporarily disabled"
                    )
                    # safe_command_name = command_name.replace(" ", "_").replace(
                    #     "/", "_")
                    # filename = f"{device_info.hostname}_{safe_command_name}.parquet"
                    # target_file_path = output_dir / filename

                    # # Time export operation
                    # export_start_time = time.perf_counter()
                    # try:
                    #     await exporter.export_data(data_list, str(target_file_path))
                    #     export_time = time.perf_counter() - export_start_time

                    #     # Log export timing with structured context
                    #     timing_logger = TimingLoggerAdapter(
                    #         logger,
                    #         operation_type="data_export",
                    #         hostname=device_info.hostname,
                    #         platform=device_info.platform,
                    #         command_name=command_name,
                    #         export_time=round(export_time, 3),
                    #         records_exported=len(data_list),
                    #         file_path=str(target_file_path),
                    #     )
                    #     timing_logger.info(
                    #         f"ExportTime: {export_time:.1f}s, "
                    #         f"Records: {len(data_list)}, "
                    #         f"File: '{Path(target_file_path).name}'"
                    #     )
                    # except OSError as e:
                    #     export_logger = DeviceLoggerAdapter(
                    #         logger,
                    #         hostname=device_info.hostname,
                    #         platform=device_info.platform,
                    #         task_descriptor="DATA_EXPORT",
                    #     )
                    #     export_logger.error(
                    #         f"File system error exporting {command_name=}: {e}"
                    #     )
                    # except Exception as e:
                    #     export_logger = DeviceLoggerAdapter(
                    #         logger,
                    #         hostname=device_info.hostname,
                    #         platform=device_info.platform,
                    #         task_descriptor="DATA_EXPORT",
                    #     )
                    #     export_logger.error(
                    #         f"Unexpected error exporting {command_name=}: {e}"
                    #     )
                    # Store data in the database with platform-prefixed table name
                    try:
                        platform_command_name = f"{platform}_{command_name}"
                        storage_service.store_command_data(
                            hostname=device_info.hostname,
                            platform=platform,
                            command_name=platform_command_name,
                            data=data_list,
                        )
                        device_logger.debug(
                            f"Command '{command_name}' collected {len(data_list)} "
                            f"records - stored as table '{platform_command_name}'"
                        )
                    except Exception as e:
                        device_logger.error(
                            f"Failed to store data for command '{command_name}': {e}"
                        )
                else:
                    device_logger.info(
                        f"No data collected for command '{command_name}'"
                    )
                    # export_logger = DeviceLoggerAdapter(
                    #     logger,
                    #     hostname=device_info.hostname,
                    #     platform=device_info.platform,
                    #     task_descriptor="DATA_EXPORT",
                    # )
                    # export_logger.info(
                    #     f"No data to export for command '{command_name}'"
                    # )

    for dc_config in device_configs:
        tasks.append(guarded_task(dc_config))

    await asyncio.gather(*tasks, return_exceptions=False)

    # Use AppLoggerAdapter for application-level completion message
    app_logger = AppLoggerAdapter(logger, operation="APPLICATION")
    app_logger.info("All device processing tasks complete")


class Collector:
    """Main collector class that encapsulates the data collection workflow.

    This class provides a clean interface for orchestrating network data
    collection operations.
    """

    def __init__(
        self,
        parser_type: str = "textfsm",
        exporter_type: str = "duckdb_parquet",
    ) -> None:
        """Initialize the collector with specified parser and exporter types.

        Args:
            parser_type: The type of parser to use for output processing.
            exporter_type: The type of exporter to use for data export.

        """
        self.parser_type = parser_type
        self.exporter_type = exporter_type

    async def collect(
        self,
        device_configs: list[Device],
        commands_by_platform: CommandsByPlatform,
        output_dir: Path,
        db_manager: DatabaseManager,
        max_concurrent_connections: int = 10,
    ) -> None:
        """Execute the main data collection workflow.

        Args:
            device_configs: List of device configurations to process.
            commands_by_platform: Mapping of platforms to their commands.
            output_dir: Directory where collected data will be saved.
            db_manager: Database manager for DuckDB operations.
            max_concurrent_connections: Maximum concurrent device connections.

        """
        logger = logging.getLogger(__name__)

        try:
            parser = ParserFactory.get_parser(self.parser_type)
            # exporter = ExporterFactory.get_exporter(self.exporter_type)
        except ValueError as e:
            logger.error("Error initializing components: %s", e)
            return

        await main_workflow(
            device_configs,
            commands_by_platform,
            max_concurrent_connections,
            output_dir,
            parser,
            db_manager,
            # exporter,
        )
