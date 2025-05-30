"""Configuration models for network device inventory and connection details."""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    PositiveInt,
    SecretStr,
    StrictBool,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from netcollector.config.utils import YamlConfigLoader

logger = logging.getLogger(__name__)


class Device(BaseSettings):
    """Model representing a connection details for a network device."""

    model_config = SettingsConfigDict(
        extra="forbid",
    )

    hostname: Annotated[str, Field(min_length=3)]
    # IP address or hostname of the device
    host: Annotated[str, Field(min_length=3)]
    port: PositiveInt | None = None
    auth_username: Annotated[str, Field(min_length=3)] | None = None
    auth_private_key: FilePath | None = None
    auth_private_key_passphrase: SecretStr | None = None
    auth_password: SecretStr | None = None
    auth_strict_key: StrictBool = False
    transport: Literal["asyncssh", "asynctelnet"] = "asyncssh"
    platform: Literal[
        "arista_eos",
        "cisco_iosxe",
        "cisco_iosxr",
        "cisco_nxos",
        "juniper_junos",
    ]

    @model_validator(mode="before")
    @classmethod
    def convert_transport(cls, values: dict) -> dict:
        """Convert transport to a more specific type."""
        transport = values.get("transport")
        if transport == "ssh":
            values["transport"] = "asyncssh"
        elif transport == "telnet":
            values["transport"] = "asynctelnet"
        return values

    @model_validator(mode="before")
    @classmethod
    def convert_password(cls, values: dict) -> dict:
        """Convert password to a more specific type."""
        auth_password = values.get("auth_password")
        # Check if it's a string
        if isinstance(auth_password, str):
            # Convert it to SecretStr
            values["auth_password"] = SecretStr(auth_password)
        return values

    @model_validator(mode="after")
    def validate_auth_method(self) -> "Device":
        """Validate that private key or password is set, but not both."""
        if self.auth_username is None:
            msg = "auth_username is required and cannot be None."
            raise ValueError(msg)
        if self.auth_private_key is None and self.auth_password is None:
            msg = "Either 'auth_private_key' or 'auth_password' must be set."
            raise ValueError(msg)
        if self.auth_private_key is not None and self.auth_password is not None:
            msg = "Set 'auth_private_key' or 'auth_password', not both."
            raise ValueError(msg)
        return self

    def __repr_args__(self) -> Sequence[tuple[str | None, Any]]:
        """Exclude None values from the representation."""
        return [
            (key, value) for key, value in super().__repr_args__() if value is not None
        ]


class Inventory(BaseModel):
    """Model representing an inventory of network devices."""

    devices: list[Device]

    @model_validator(mode="after")
    def validate_unique_hostnames(self) -> "Inventory":
        """Validate that all device hostnames are unique (case-insensitive)."""
        seen_hostnames: set[str] = set()
        for device in self.devices:
            hostname_lower = device.hostname.lower()
            if hostname_lower in seen_hostnames:
                msg = (
                    f"Duplicate hostname found: {device.hostname}. "
                    "Hostnames must be unique (case-insensitive)."
                )
                raise ValueError(msg)
            seen_hostnames.add(hostname_lower)
        return self


def _apply_device_defaults(
    device_data: dict,
    default_user: str,
    default_password: SecretStr | None,
    default_private_key: Path | None,
    default_private_key_passphrase: SecretStr | None,
) -> None:
    """Apply default authentication values to a device configuration.

    Args:
        device_data: Dictionary containing device configuration data.
        default_user: Default username to use for devices without
            auth_username.
        default_password: Default password to use for devices without
            auth_password.
        default_private_key: Default private key path to use for devices
            without auth_private_key.
        default_private_key_passphrase: Default private key passphrase to use
            for devices without auth_private_key_passphrase.

    """
    # Apply default username if not provided
    if device_data.get("auth_username") is None:
        device_data["auth_username"] = default_user

    # Apply default password if no auth method is specified
    if (
        device_data.get("auth_password") is None
        and device_data.get("auth_private_key") is None
    ):
        device_data["auth_password"] = default_password

    # Apply default private_key if provided
    if device_data.get("auth_private_key") is None and default_private_key is not None:
        device_data["auth_private_key"] = default_private_key

    # Apply default private_key_passphrase if provided
    if (
        device_data.get("auth_private_key_passphrase") is None
        and default_private_key_passphrase is not None
    ):
        device_data["auth_private_key_passphrase"] = default_private_key_passphrase


def load_inventory(
    inventory_file: FilePath,
    default_user: str,
    default_password: SecretStr | None,
    default_private_key: Path | None,
    default_private_key_passphrase: SecretStr | None,
) -> Inventory | None:
    """Load inventory from a YAML file.

    Args:
        inventory_file: Path to the inventory YAML file.
        default_user: Default username to use for devices without auth_username.
        default_password: Default password to use for devices without auth_password.
        default_private_key: Default private key path to use for devices without
            auth_private_key.
        default_private_key_passphrase: Default private key passphrase to use for
            devices without auth_private_key_passphrase.

    Returns:
        Inventory if successful, None if there are errors.

    """

    def pre_process_inventory(yaml_data: dict[str, Any]) -> dict[str, Any]:
        """Apply device defaults to inventory data."""
        if "devices" in yaml_data:
            for device_data in yaml_data["devices"]:
                _apply_device_defaults(
                    device_data,
                    default_user,
                    default_password,
                    default_private_key,
                    default_private_key_passphrase,
                )
        return yaml_data

    try:
        return YamlConfigLoader.load(
            model_class=Inventory,
            yaml_file=inventory_file,
            pre_process_hook=pre_process_inventory,
        )
    except Exception:
        # Return None on any error to match original signature
        return None
