"""Core interfaces for the collector module.

This module defines the fundamental contracts that parsers and exporters
must implement to work within the collection framework.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from scrapli.response import Response as ScrapliResponse

if TYPE_CHECKING:
    from netcollector.config.commands import CommandDetail

# Type Aliases for stricter typing
type PrimitiveDataValue = str | int | float | bool | None
type ParsedRecord = dict[str, PrimitiveDataValue]
type ParsedData = list[ParsedRecord]


class IOutputParser(ABC):
    """Interface for output parsers.

    Defines a standard contract for parsing raw command output from network
    devices.
    """

    @abstractmethod
    def parse(
        self, response: ScrapliResponse, hostname: str | None = None
    ) -> ParsedData:
        """Parse raw output string.

        Scrapli will attempt to automatically find the appropriate TextFSM
        template based on the command and platform.

        Args:
            response: Scrapli Style Response containing the command output.
            hostname: Optional hostname for logging purposes. If not provided,
                     response.host will be used.

        Returns:
            A list of dictionaries with parsed data. Returns an
            empty list if parsing fails.

        """


class IDataNormalizer(ABC):
    """Interface for data normalizers.

    Defines a standard contract for normalizing parsed command output.
    """

    @abstractmethod
    def normalize(
        self,
        parsed_data: ParsedData,
        command_detail: "CommandDetail",
        hostname: str | None = None,
        platform: str | None = None,
        command_name: str | None = None,
    ) -> ParsedData:
        """Normalize parsed data based on configuration.

        Applies transformations such as key renaming, key dropping, and null key
        addition to ensure consistent data structure across different devices
        and commands.

        Args:
            parsed_data: List of dictionaries containing parsed command output.
            command_detail: Configuration object with normalization rules.
            hostname: Optional hostname for logging purposes.
            platform: Optional platform identifier for logging purposes.
            command_name: Optional command name for logging purposes.

        Returns:
            Normalized ParsedData with transformations applied.

        """


class IDataExporter(ABC):
    """Interface for data exporters.

    Defines a standard contract for exporting processed data.
    """

    @abstractmethod
    async def export_data(self, data: ParsedData, target_path: str) -> None:
        """Export data to a specified target path.

        Args:
            data: A list of dictionaries containing the data to export.
            target_path: The path (e.g., file path) where the data should be
                        exported.

        """
