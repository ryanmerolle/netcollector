"""Data storage service for persisting collected network data.

This module provides services for storing parsed and normalized network device
data into the DuckDB database during the collection process.
"""

import logging
from typing import TYPE_CHECKING, Any

import duckdb

from netcollector.utils.database import DatabaseManager
from netcollector.utils.logging import DeviceLoggerAdapter

if TYPE_CHECKING:
    from netcollector.collector.interfaces import ParsedData


class DataStorageService:
    """Service for storing collected network data into DuckDB tables.

    This service handles the creation of tables and insertion of data
    during the collection process, making the data available for
    processing and export operations.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the data storage service.

        Args:
            db_manager: Database manager instance for DuckDB operations.

        """
        self.db_manager = db_manager

    def store_command_data(
        self,
        hostname: str,
        platform: str,
        command_name: str,
        data: "ParsedData",
    ) -> None:
        """Store parsed command data in the database.

        Creates a table if it doesn't exist and inserts the data records.
        The table name is generated from the command name to organize data
        by command type.

        Args:
            hostname: The hostname of the device the data came from.
            platform: The platform/OS of the device.
            command_name: The name of the command that generated this data.
            data: List of dictionaries containing the parsed command output.

        """
        if not data:
            return

        logger = logging.getLogger(__name__)
        device_logger = DeviceLoggerAdapter(
            logger,
            hostname=hostname,
            platform=platform,
            task_descriptor="DATA_STORAGE",
        )

        # Create a safe table name from the command name
        table_name = self._create_table_name(command_name)

        try:
            with self.db_manager.get_connection() as conn:
                # Create table if it doesn't exist based on the first record
                self._ensure_table_exists(conn, table_name, data[0])

                # Insert all records
                self._insert_records(conn, table_name, data)

                device_logger.debug(
                    f"Stored {len(data)} records for command '{command_name}' "
                    f"in table '{table_name}'"
                )

        except Exception as e:
            device_logger.error(
                f"Failed to store data for command '{command_name}': {e}"
            )
            raise

    def _create_table_name(self, command_name: str) -> str:
        """Create a safe table name from a command name.

        Args:
            command_name: The original command name.

        Returns:
            A sanitized table name safe for SQL use.

        """
        # Replace spaces and special characters with underscores
        safe_name = command_name.lower().replace(" ", "_").replace("-", "_")
        # Remove any remaining non-alphanumeric characters except underscores
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        # Ensure it starts with a letter
        if safe_name and not safe_name[0].isalpha():
            safe_name = f"cmd_{safe_name}"
        return safe_name or "unknown_command"

    def _ensure_table_exists(
        self,
        conn: duckdb.DuckDBPyConnection,
        table_name: str,
        sample_record: dict[str, Any],
    ) -> None:
        """Ensure a table exists for the given data structure.

        Args:
            conn: DuckDB connection.
            table_name: Name of the table to create.
            sample_record: Sample record to determine column types.

        """
        # Build column definitions based on the sample record
        columns = []
        for key, value in sample_record.items():
            # Determine SQL type based on Python type
            if isinstance(value, bool):
                sql_type = "BOOLEAN"
            elif isinstance(value, int):
                sql_type = "INTEGER"
            elif isinstance(value, float):
                sql_type = "DOUBLE"
            else:
                sql_type = "VARCHAR"

            # Escape column name if it's a SQL keyword
            safe_column_name = f'"{key}"' if self._is_sql_keyword(key) else key
            columns.append(f"{safe_column_name} {sql_type}")

        columns_sql = ", ".join(columns)
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"

        conn.execute(create_table_sql)

    def _insert_records(
        self, conn: duckdb.DuckDBPyConnection, table_name: str, data: "ParsedData"
    ) -> None:
        """Insert records into the specified table.

        Args:
            conn: DuckDB connection.
            table_name: Name of the table to insert into.
            data: List of dictionaries to insert.

        """
        if not data:
            return

        # Get column names from the first record
        columns = list(data[0].keys())
        safe_columns = [
            f'"{col}"' if self._is_sql_keyword(col) else col for col in columns
        ]
        columns_sql = ", ".join(safe_columns)

        # Create placeholders for values
        placeholders = ", ".join(["?" for _ in columns])
        insert_sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders})"

        # Prepare data rows, ensuring consistent column order
        rows = []
        for record in data:
            row = [record.get(col) for col in columns]
            rows.append(row)

        # Execute batch insert
        conn.executemany(insert_sql, rows)

    def _is_sql_keyword(self, word: str) -> bool:
        """Check if a word is a SQL keyword that needs escaping.

        Args:
            word: The word to check.

        Returns:
            True if the word is a SQL keyword.

        """
        sql_keywords = {
            "select",
            "from",
            "where",
            "insert",
            "update",
            "delete",
            "create",
            "drop",
            "alter",
            "table",
            "index",
            "view",
            "grant",
            "revoke",
            "union",
            "order",
            "group",
            "having",
            "distinct",
            "count",
            "sum",
            "avg",
            "max",
            "min",
            "and",
            "or",
            "not",
            "null",
            "is",
            "in",
            "between",
            "like",
            "exists",
            "case",
            "when",
            "then",
            "else",
            "end",
            "as",
            "on",
            "join",
            "inner",
            "left",
            "right",
            "full",
            "outer",
            "cross",
            "natural",
            "using",
        }
        return word.lower() in sql_keywords

    def get_table_info(self) -> list[dict[str, Any]]:
        """Get information about all tables in the database.

        Returns:
            List of dictionaries containing table information.

        """
        try:
            with self.db_manager.get_connection() as conn:
                result = conn.execute("SHOW TABLES").fetchall()

                tables_info = []
                for (table_name,) in result:
                    # Get column count for each table
                    column_result = conn.execute(
                        f"SELECT COUNT(*) FROM information_schema.columns "
                        f"WHERE table_name = '{table_name}'"
                    ).fetchone()
                    column_count = column_result[0] if column_result else 0

                    tables_info.append(
                        {"table_name": table_name, "column_count": column_count}
                    )

                return tables_info
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get table information: {e}")
            return []

    def get_table_row_count(self, table_name: str) -> int:
        """Get the number of rows in a specific table.

        Args:
            table_name: Name of the table to count.

        Returns:
            Number of rows in the table, or 0 if table doesn't exist.

        """
        try:
            with self.db_manager.get_connection() as conn:
                result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                return result[0] if result else 0
        except Exception:
            return 0
