"""Data exporter implementations.

This module contains concrete implementations of data exporters that can
export processed data to various formats and destinations.
"""

import asyncio
import logging
from pathlib import Path

import duckdb
import pyarrow as pa

from netcollector.collector.interfaces import IDataExporter, ParsedData


class DuckDBParquetExporter(IDataExporter):
    """Exports data to a Parquet file using DuckDB for efficient processing.

    This exporter leverages DuckDB's ability to handle large datasets and
    its direct integration with Apache Arrow for creating Parquet files.
    """

    async def export_data(
        self,
        data: ParsedData,
        target_path: str,
        table_name: str = "export_table",
    ) -> None:
        """Export data to a Parquet file via DuckDB.

        Uses DuckDB to create a table from the data (via an Arrow table)
        and then exports it. The synchronous DuckDB operations are run in a
        separate thread to maintain asynchronous compatibility.

        Args:
            data: A list of dictionaries to be exported.
            target_path: The file path for the output Parquet file.
            table_name: Name for the transient DuckDB table during export.
                        Defaults to "export_table".

        """
        logger = logging.getLogger(__name__)

        if not data:
            logger.warning("No data provided to export to %s", target_path)
            return

        target_path_str = str(target_path)

        def _export_sync() -> None:
            conn = None
            try:
                conn = duckdb.connect(database=":memory:", read_only=False)
                arrow_table = pa.Table.from_pylist(data)
                conn.register("arrow_data_view", arrow_table)

                path_obj = Path(target_path_str)
                path_obj.parent.mkdir(parents=True, exist_ok=True)

                conn.execute(
                    f"COPY (SELECT * FROM arrow_data_view) TO '{target_path_str}' "
                    f"(FORMAT PARQUET, CODEC 'ZSTD', OVERWRITE_OR_IGNORE TRUE);"
                )
                # Removed duplicate success log - handled by orchestrator timing logger

            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Error exporting to %s with DuckDB: %s", target_path_str, e
                )
            finally:
                if conn:
                    conn.close()

        try:
            await asyncio.to_thread(_export_sync)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                "Async wrapper error for DuckDB export to %s: %s", target_path_str, e
            )
