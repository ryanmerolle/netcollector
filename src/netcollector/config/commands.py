"""Commands to be executed on network devices and mapped to tables."""

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from netcollector.config.utils import YamlConfigLoader, get_package_file

logger = logging.getLogger(__name__)


class CommandDetail(BaseModel):
    """Configuration for a command to be executed.

    This class defines how a command should be executed and how its output
    should be processed, including parsing, normalization, and data transformations.

    Attributes:
        command: The actual command string to execute on the network device.
        textfsm_template: Optional custom TextFSM template name to use for parsing.
            If None, Scrapli will auto-detect the appropriate template.
        rename_keys: Optional mapping of old key names to new key names.
            Applied during normalization to standardize field names.
        keys_to_drop: Optional list of key names to remove from parsed records.
            Useful for filtering out unwanted or sensitive data.
        null_keys: Optional list of key names to add with null values if they
            don't already exist in the parsed records. If a key already exists,
            it will be set to None with a warning logged.

    """

    command: str
    textfsm_template: str | None = None
    rename_keys: dict[str, str] | None = None
    keys_to_drop: list[str] | None = None
    null_keys: list[str] | None = None


class CommandsByPlatform(BaseModel):
    """Configuration for platform-specific command configuration."""

    arista_eos: dict[str, CommandDetail] = {}
    cisco_iosxe: dict[str, CommandDetail] = {}
    cisco_iosxr: dict[str, CommandDetail] = {}
    cisco_nxos: dict[str, CommandDetail] = {}
    juniper_junos: dict[str, CommandDetail] = {}

    def get(self, platform: str) -> dict[str, CommandDetail] | None:
        """Get commands for a specific platform.

        Args:
            platform: The platform name (e.g., "cisco_iosxe").

        Returns:
            Dictionary of command names to CommandDetail objects for the platform,
            or None if platform not found.

        """
        return getattr(self, platform, None)


def load_commands(commands_file: Path | None = None) -> CommandsByPlatform:
    """Load commands configuration from a YAML file.

    Args:
        commands_file: Path to the commands YAML file. If None, uses default
            package file.

    Returns:
        CommandsByPlatform: The loaded and validated commands configuration.

    Raises:
        ConfigLoadError: If there are validation errors or file loading issues.

    """
    if commands_file is None:
        commands_file = get_package_file("commands.yaml")

    def pre_process_commands(yaml_data: dict[str, Any]) -> dict[str, Any]:
        """Pre-process commands YAML data to match CommandsByPlatform model."""
        # Use platforms structure if available, otherwise fall back to platforms
        if "platforms" in yaml_data:
            platforms_data = yaml_data["platforms"]
            # Convert command dictionaries to CommandDetail objects for each platform
            for platform_name, commands_dict in platforms_data.items():
                if isinstance(commands_dict, dict):
                    platforms_data[platform_name] = {
                        cmd_name: CommandDetail.model_validate(cmd_config)
                        for cmd_name, cmd_config in commands_dict.items()
                    }
            return platforms_data
        elif "platforms" in yaml_data:
            # Legacy format support
            platforms_data = yaml_data["platforms"]
            for platform_name, commands_list in platforms_data.items():
                if isinstance(commands_list, list):
                    # Convert list format to dict format
                    commands_dict = {}
                    for cmd in commands_list:
                        cmd_detail = CommandDetail.model_validate(cmd)
                        commands_dict[cmd["name"]] = cmd_detail
                    platforms_data[platform_name] = commands_dict
            return platforms_data
        return yaml_data

    return YamlConfigLoader.load(
        model_class=CommandsByPlatform,
        yaml_file=commands_file,
        pre_process_hook=pre_process_commands,
    )
