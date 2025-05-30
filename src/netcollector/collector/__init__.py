"""Network data collector module.

This module provides the core functionality for collecting, parsing, and
exporting data from network devices.
"""

from netcollector.collector.exporters import DuckDBParquetExporter
from netcollector.collector.factories import ExporterFactory, ParserFactory
from netcollector.collector.interfaces import IDataExporter, IOutputParser
from netcollector.collector.orchestrator import Collector, main_workflow
from netcollector.collector.parsers import TextFSMParser

__all__ = [
    "Collector",
    "DuckDBParquetExporter",
    "ExporterFactory",
    "IDataExporter",
    "IOutputParser",
    "ParserFactory",
    "TextFSMParser",
    "main_workflow",
]
