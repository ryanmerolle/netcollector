"""Data normalization utilities for processing parsed command output.

This module contains concrete implementations of data normalizers that can
process parsed command output by applying transformations like key renaming,
dropping unwanted keys, and adding null keys based on CommandDetail configuration.
"""

import logging

from netcollector.collector.interfaces import IDataNormalizer, ParsedData, ParsedRecord
from netcollector.config.commands import CommandDetail
from netcollector.utils.logging import DeviceLoggerAdapter


class DataNormalizer(IDataNormalizer):
    """A normalizer that applies transformations to parsed command output.

    This normalizer can perform the following transformations based on
    CommandDetail configuration:
    - Drop unwanted keys from records
    - Rename keys to standardize field names
    - Add null keys to ensure consistent record structure
    """

    def normalize(
        self,
        parsed_data: ParsedData,
        command_detail: CommandDetail,
        hostname: str | None = None,
        platform: str | None = None,
        command_name: str | None = None,
    ) -> ParsedData:
        """Normalize parsed data based on CommandDetail configuration.

        Applies transformations like key renaming, key dropping, and null key addition
        to the parsed data according to the configuration in CommandDetail.

        The normalization process applies transformations in this order:
        1. Drop unwanted keys (keys_to_drop)
        2. Rename keys (rename_keys)
        3. Add null keys (null_keys)

        Args:
            parsed_data: List of dictionaries containing parsed command output.
            command_detail: Configuration object with normalization rules.
            hostname: Optional hostname for logging purposes.
            platform: Optional platform identifier for logging purposes.
            command_name: Optional command name for logging purposes.

        Returns:
            Normalized ParsedData with transformations applied. Returns an
            empty list if normalization fails.

        """
        base_logger = logging.getLogger(__name__)

        # Create device-specific logger for normalization operations
        normalizer_logger = DeviceLoggerAdapter(
            base_logger,
            hostname=hostname,
            platform=platform,
            task_descriptor="DATA_NORMALIZATION",
        )

        try:
            if not parsed_data:
                normalizer_logger.debug(
                    f"No data to normalize for command '{command_name}'"
                )
                return parsed_data

            normalized_data: ParsedData = []

            for record in parsed_data:
                normalized_record = self._normalize_record(
                    record, command_detail, normalizer_logger, command_name
                )
                if normalized_record:  # Only add non-empty records
                    normalized_data.append(normalized_record)

            normalizer_logger.debug(
                f"Normalized {len(parsed_data)} records to {len(normalized_data)} "
                f"records for command '{command_name}'"
            )

            return normalized_data

        except (AttributeError, KeyError, TypeError, ValueError) as e:
            normalizer_logger.error(
                f"Data normalization error for command '{command_name}': {e}"
            )
            return []

    def _normalize_record(
        self,
        record: ParsedRecord,
        command_detail: CommandDetail,
        logger: DeviceLoggerAdapter,
        command_name: str | None = None,
    ) -> ParsedRecord:
        """Normalize a single parsed record.

        Applies all configured transformations to a single record in this order:
        1. Drop unwanted keys (keys_to_drop)
        2. Rename keys (rename_keys)
        3. Add null keys (null_keys) - adds keys with None values if they
            don't exist, or sets existing keys to None with a warning

        Args:
            record: Single dictionary record to normalize.
            command_detail: Configuration object with normalization rules.
            logger: Logger instance for debug/error messages.
            command_name: Optional command name for logging purposes.

        Returns:
            Normalized record with transformations applied.

        """
        # Start with a copy of the original record
        normalized_record: ParsedRecord = record.copy()

        # Apply key dropping if configured
        if command_detail.keys_to_drop:
            normalized_record = self._drop_keys(
                normalized_record, command_detail.keys_to_drop, logger, command_name
            )

        # Apply key renaming if configured
        if command_detail.rename_keys:
            normalized_record = self._rename_keys(
                normalized_record, command_detail.rename_keys, logger, command_name
            )

        # Handle null keys if configured
        if command_detail.null_keys:
            for null_key in command_detail.null_keys:
                if null_key in normalized_record:
                    # log warning that key is already in present
                    logger.warning(
                        f"Key '{null_key}' already exists in record for command "
                        f"'{command_name}'. Setting it to None."
                    )
                else:
                    # Set the key to None if it doesn't exist
                    normalized_record[null_key] = None
                    logger.debug(
                        f"Set key '{null_key}' to None for command '{command_name}'"
                    )

        return normalized_record

    def _rename_keys(
        self,
        record: ParsedRecord,
        rename_mapping: dict[str, str],
        logger: DeviceLoggerAdapter,
        command_name: str | None = None,
    ) -> ParsedRecord:
        """Rename keys in a record based on the provided mapping.

        Args:
            record: The record to modify.
            rename_mapping: Dictionary mapping old key names to new key names.
            logger: Logger instance for debug messages.
            command_name: Optional command name for logging purposes.

        Returns:
            Record with renamed keys.

        """
        renamed_record: ParsedRecord = {}

        for old_key, value in record.items():
            new_key = rename_mapping.get(old_key, old_key)
            renamed_record[new_key] = value

            if new_key != old_key:
                logger.debug(
                    f"Renamed key '{old_key}' to '{new_key}' "
                    f"for command '{command_name}'"
                )

        return renamed_record

    def _drop_keys(
        self,
        record: ParsedRecord,
        keys_to_drop: list[str],
        logger: DeviceLoggerAdapter,
        command_name: str | None = None,
    ) -> ParsedRecord:
        """Drop specified keys from a record.

        Args:
            record: The record to modify.
            keys_to_drop: List of key names to remove from the record.
            logger: Logger instance for debug messages.
            command_name: Optional command name for logging purposes.

        Returns:
            Record with specified keys removed.

        """
        filtered_record: ParsedRecord = {}

        for key, value in record.items():
            if key not in keys_to_drop:
                filtered_record[key] = value
            else:
                logger.debug(f"Dropped key '{key}' for command '{command_name}'")

        return filtered_record
