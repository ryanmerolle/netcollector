"""Factory classes for creating parser and exporter instances.

This module provides factory classes that encapsulate the instantiation logic
for different types of parsers and exporters, making it easy to extend with
new implementations.
"""

from netcollector.collector.exporters import DuckDBParquetExporter
from netcollector.collector.interfaces import IDataExporter, IOutputParser
from netcollector.collector.parsers import TextFSMParser


class ParserFactory:
    """Factory for creating parser instances."""

    @staticmethod
    def get_parser(parser_type: str = "textfsm") -> IOutputParser:
        """Get an instance of the specified parser type.

        Args:
            parser_type: The type of parser to create (e.g., "textfsm").
                        Defaults to "textfsm".

        Returns:
            An instance of IOutputParser.

        Raises:
            ValueError: If the specified parser_type is unsupported.

        """
        if parser_type == "textfsm":
            return TextFSMParser()
        raise ValueError(f"Unsupported parser type: {parser_type}")


class ExporterFactory:
    """Factory for creating exporter instances."""

    @staticmethod
    def get_exporter(exporter_type: str = "duckdb_parquet") -> IDataExporter:
        """Get an instance of the specified exporter type.

        Args:
            exporter_type: The type of exporter to create
                        (e.g., "duckdb_parquet").
                        Defaults to "duckdb_parquet".

        Returns:
            An instance of IDataExporter.

        Raises:
            ValueError: If the specified exporter_type is unsupported.

        """
        if exporter_type == "duckdb_parquet":
            return DuckDBParquetExporter()
        raise ValueError(f"Unsupported exporter type: {exporter_type}")
