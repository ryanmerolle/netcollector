"""Export data to a readable file."""

import logging
from enum import StrEnum
from typing import Annotated

import typer

from netcollector.cli.utils import version_callback

app = typer.Typer()


class ExportFileType(StrEnum):
    """Supported export file types."""

    EXCEL = "xlsx"
    CSV = "csv"
    JSON = "json"
    YAML = "yaml"
    PARQUET = "parquet"


def get_default_file_extension(file_type: str) -> str:
    """Get the default file extension for export.

    Args:
        file_type (str): The type of file to export.

    Returns:
        str: The default file extension for the given file type.

    """
    match file_type:
        case ExportFileType.EXCEL:
            return "xlsx"
        case ExportFileType.CSV:
            return "csv"
        case ExportFileType.JSON:
            return "json"
        case ExportFileType.YAML:
            return "yaml"
        case ExportFileType.PARQUET:
            return "parquet"
        case _:
            return "xlsx"


@app.command()
def export(
    show_version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        rich_help_panel="Options",
        help="Print the version and exit",
    ),
    file_type: Annotated[str, typer.Argument()] = "excel",
) -> None:
    """Export data to a readable file."""
    _ = show_version

    logger = logging.getLogger(__name__)
    logger.info(
        "Exporting data as %s to file %s with file extension %s...",
        file_type,
        get_default_file_extension(file_type),
    )
