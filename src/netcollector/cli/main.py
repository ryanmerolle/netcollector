"""Main entry point for the CLI."""

import typer

from netcollector.cli.collect import collect
from netcollector.cli.export import export
from netcollector.cli.utils import version_callback

app = typer.Typer(
    name="netcollector",
    help="Network collector CLI tool",
    add_completion=False,
    pretty_exceptions_enable=False,
)

app.command("collect")(collect)
app.command("export")(export)


@app.callback()
def version(
    show_version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        rich_help_panel="Options",
        help="Print the version and exit",
    ),
) -> None:
    """Handle CLI callback and version option."""
    _ = show_version
