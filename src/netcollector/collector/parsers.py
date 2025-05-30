"""Parser implementations for network device output.

This module contains concrete implementations of output parsers that can
process raw command output from network devices into structured data.
"""

import logging
from typing import Any

from scrapli.response import Response as ScrapliResponse

from netcollector.collector.interfaces import IOutputParser, ParsedData
from netcollector.utils.logging import DeviceLoggerAdapter


class TextFSMParser(IOutputParser):
    """A parser that uses TextFSM to parse semi-structured CLI output."""

    def parse(
        self,
        response: ScrapliResponse,
        hostname: str | None = None,
        platform: str | None = None,
    ) -> ParsedData:
        """Parse raw output using Scrapli's built-in TextFSM capability.

        Scrapli will attempt to automatically find the appropriate TextFSM
        template based on the command and platform.

        Args:
            response: Scrapli Style Response containing the command output.
            hostname: Optional hostname for logging purposes. If not provided,
                    response.host will be used.
            platform: Optional platform identifier for logging purposes.

        Returns:
            A list of dictionaries with parsed data. Returns an
            empty list if parsing fails.

        """
        base_logger = logging.getLogger(__name__)

        # Use hostname if provided, otherwise fall back to response.host
        device_identifier = hostname if hostname is not None else response.host

        # Create device-specific logger for parsing operations
        parser_logger = DeviceLoggerAdapter(
            base_logger,
            hostname=device_identifier,
            platform=platform,
            task_descriptor="DATA_PARSING",
        )

        try:
            # Scrapli's textfsm_parse_output can return List[Dict[str, Any]]
            # or Dict[str, Any] depending on the template and output.
            # We expect a list of records (ParsedData).
            # TODO: Move to own TextFSMParser class
            parsed_output: Any = response.textfsm_parse_output()

            # Ensure parsed_output is a list, as expected by ParsedData.
            # If it's a single dictionary (e.g. show version), wrap it in a list.
            if isinstance(parsed_output, dict):
                parsed_data: ParsedData = [parsed_output]  # type: ignore
            elif isinstance(parsed_output, list):
                parsed_data = parsed_output  # type: ignore
            else:
                # If it's neither a list nor a dict, it's an unexpected type.
                parser_logger.warning(
                    f"TextFSM parsing returned unexpected data type: "
                    f"{type(parsed_output)} for command '{response.channel_input}'"
                )
                return []

            if not parsed_data:
                parser_logger.warning(
                    f"TextFSM parsing yielded no results for command "
                    f"'{response.channel_input}'. Check if ntc-template."
                )
                response_platform = response.textfsm_platform
                raw_response = response.raw_result
                parser_logger.debug(
                    f"Raw response result for command '{response.channel_input}': "
                    f"{response_platform=} {raw_response=}"
                )
            else:
                parser_logger.debug(
                    f"TextFSM parsing completed successfully for command "
                    f"'{response.channel_input}' - {len(parsed_data)} records found"
                )
            return parsed_data
        except Exception as e:
            parser_logger.error(
                f"TextFSM parsing error for command '{response.channel_input}': {e}"
            )
            return []
