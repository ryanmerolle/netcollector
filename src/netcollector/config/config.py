"""Configuration models for the app."""

from pathlib import Path

from pydantic import BaseModel, PositiveFloat, PositiveInt

from netcollector.config.logging import LoggingConfig
from netcollector.config.utils import YamlConfigLoader


class Config(BaseModel):
    """Configuration for the application."""

    logging: LoggingConfig = LoggingConfig()
    artifacts_path: Path = Path.cwd() / ".artifacts"
    # commands_file_path: FilePath =
    # inventory_file_path: FilePath =
    # commands: CommandsByPlatform
    # inventory: Inventory  # Changed from InventoryConfig
    max_concurrent_tasks: PositiveInt = 10
    scrapli_timeout: PositiveFloat = 30.0
    interface_keys: list[str] = [
        "incoming_interface",
        "interface",
        "neighbor_interface",
        "nexthop_if",
    ]
    interface_list_keys: list[str] = [
        "interface_list",
        "interface_lists",
        "interfaces_list",
        "member_interfaces",
        "oif_list",
    ]


def load_config(config_file: Path | None) -> "Config":
    """Load configuration from a file."""

    def default_config() -> "Config":
        """Create a default configuration."""
        return Config(logging=LoggingConfig())

    if config_file is None:
        return default_config()

    return YamlConfigLoader.load(
        model_class=Config,
        yaml_file=config_file,
        default_factory=default_config,
    )
