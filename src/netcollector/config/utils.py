"""Utility functions for configuration management."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from pydantic_core import ErrorDetails

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class YamlConfigLoader:
    """Generic YAML configuration loader factory for Pydantic models."""

    @staticmethod
    def load(
        model_class: type[T],
        yaml_file: Path,
        pre_process_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        default_factory: Callable[[], T] | None = None,
    ) -> T:
        """Load and validate a YAML configuration file into a Pydantic model.

        Args:
            model_class: The Pydantic model class to validate against.
            yaml_file: Path to the YAML configuration file.
            pre_process_hook: Optional function to pre-process the raw YAML
                data before validation.
            default_factory: Optional function to create a default instance
                if the file doesn't exist or is empty.

        Returns:
            An instance of the specified Pydantic model.

        Raises:
            ConfigLoadError: If there are validation errors or file loading
                issues.

        """
        from netcollector.exceptions import ConfigLoadError

        # Handle missing or empty file with defaults
        if not yaml_file.exists() or yaml_file.stat().st_size == 0:
            return YamlConfigLoader._handle_missing_or_empty_file(
                yaml_file, default_factory
            )

        try:
            yaml_data = YamlConfigLoader._load_yaml_data(yaml_file)

            if yaml_data is None:
                return YamlConfigLoader._handle_missing_or_empty_file(
                    yaml_file, default_factory, "contains no data"
                )

            # Apply pre-processing hook if provided
            if pre_process_hook:
                yaml_data = pre_process_hook(yaml_data)

            # Validate against the model
            return model_class.model_validate(yaml_data)

        except FileNotFoundError as exc:
            logger.error("Configuration file %s does not exist.", yaml_file)
            msg = f"Configuration file {yaml_file} does not exist."
            raise ConfigLoadError(msg) from exc
        except ValidationError as exc:
            error_msg = validation_errors(filepath=yaml_file.name, errors=exc.errors())
            logger.error(error_msg)
            raise ConfigLoadError(error_msg) from exc
        except Exception as exc:
            logger.error("Failed to load configuration: %s", exc)
            msg = f"Failed to load configuration from {yaml_file}: {exc}"
            raise ConfigLoadError(msg) from exc

    @staticmethod
    def _handle_missing_or_empty_file(
        yaml_file: Path,
        default_factory: Callable[[], T] | None,
        reason: str = "does not exist or is empty",
    ) -> T:
        """Handle missing or empty configuration files."""
        from netcollector.exceptions import ConfigLoadError

        if default_factory:
            logger.info(
                "Configuration file %s %s, using defaults.",
                yaml_file,
                reason,
            )
            return default_factory()
        else:
            logger.error("Configuration file %s %s.", yaml_file, reason)
            msg = f"Configuration file {yaml_file} {reason}."
            raise ConfigLoadError(msg)

    @staticmethod
    def _load_yaml_data(yaml_file: Path) -> dict[str, Any] | None:
        """Load YAML data from file."""
        with Path.open(yaml_file, encoding="utf-8") as file:
            return yaml.safe_load(file)


def validation_errors(
    filepath: str,
    errors: list["ErrorDetails"] | list[dict[str, Any]],
) -> str:
    """Format validation errors into a human-readable string.

    Args:
        filepath: The path to the configuration file.
        errors: A list of validation errors.

    Returns:
        A formatted string describing the validation errors.

    """
    sp_4 = " " * 4
    as_human = ["Configuration errors", f"{sp_4}File:[{filepath}]"]

    for _err in errors:
        if isinstance(_err, dict):
            loc_str = ".".join(map(str, _err.get("loc", [])))
            msg = _err.get("msg", "Unknown error")
            as_human.append(f"{sp_4}Section: [{loc_str}]: {msg}")
        else:
            # Handle pydantic_core.ErrorDetails objects
            loc_str = ".".join(map(str, getattr(_err, "loc", [])))
            msg = getattr(_err, "msg", "Unknown error")
            as_human.append(f"{sp_4}Section: [{loc_str}]: {msg}")

    return "\\n".join(as_human)


def get_package_file(relative_file_path: str) -> Path:
    """Get the absolute path to a file within the package.

    Args:
        relative_file_path: The relative path to the file within the config
            package.

    Returns:
        The absolute path to the file.

    """
    package_dir = Path(__file__).parent
    return package_dir / relative_file_path


def get_cwd_file(relative_file_path: str) -> Path:
    """Get the absolute path to a file in the current working directory.

    Args:
        relative_file_path: The relative path to the file from the current
            working directory.

    Returns:
        The absolute path to the file.

    """
    return Path.cwd() / relative_file_path
