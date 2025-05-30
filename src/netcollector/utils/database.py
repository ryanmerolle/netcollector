"""Database utilities for DuckDB operations.

This module provides utilities for creating and managing a persistent DuckDB
database file that's used throughout the collection, processing, and
normalization workflow.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from netcollector.utils.logging import AppLoggerAdapter

if TYPE_CHECKING:
    pass


class DatabaseManager:
    """Manages the lifecycle of a DuckDB database file for collection artifacts.

    This class handles creating a timestamped DuckDB file at the start of the
    collection process and provides a clean interface for other components to
    interact with the database.
    """

    def __init__(self, artifacts_path: Path) -> None:
        """Initialize the database manager.

        Args:
            artifacts_path: The base path where artifacts (including the database)
                          will be stored.

        """
        self.artifacts_path = artifacts_path
        self._db_path: Path | None = None
        self._connection: duckdb.DuckDBPyConnection | None = None

    def create_database(self) -> Path:
        """Create a timestamped DuckDB file in the artifacts directory.

        Creates the artifacts directory if it doesn't exist and generates a
        DuckDB file with a timestamp in the name for this collection session.

        Returns:
            Path to the created DuckDB file.

        Raises:
            OSError: If the artifacts directory cannot be created or the database
                    file cannot be created.

        """
        logger = logging.getLogger(__name__)
        app_logger = AppLoggerAdapter(logger, operation="DATABASE_SETUP")

        # Ensure artifacts directory exists
        try:
            self.artifacts_path.mkdir(parents=True, exist_ok=True)
            app_logger.debug(f"Artifacts directory ensured: {self.artifacts_path}")
        except OSError as e:
            app_logger.error(f"Failed to create artifacts directory: {e}")
            raise

        # Generate timestamped database filename
        # Using local time for file naming purposes
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005
        db_filename = f"netcollector_{timestamp}.duckdb"
        self._db_path = self.artifacts_path / db_filename

        # Create the DuckDB file by connecting to it
        try:
            # Create an initial connection to ensure the file is created
            with duckdb.connect(str(self._db_path)) as conn:
                # Execute a simple query to initialize the database
                conn.execute("CREATE TABLE IF NOT EXISTS _init_check (id INTEGER)")
                conn.execute("DROP TABLE _init_check")

            app_logger.info(f"Created DuckDB file: {self._db_path.name}")
            return self._db_path

        except Exception as e:
            app_logger.error(f"Failed to create DuckDB file '{db_filename}': {e}")
            raise

    @property
    def db_path(self) -> Path:
        """Get the path to the current database file.

        Returns:
            Path to the DuckDB file.

        Raises:
            RuntimeError: If no database has been created yet.

        """
        if self._db_path is None:
            msg = "Database not created yet. Call create_database() first."
            raise RuntimeError(msg)
        return self._db_path

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a connection to the DuckDB database.

        Returns:
            A DuckDB connection object.

        Raises:
            RuntimeError: If no database has been created yet.

        """
        if self._db_path is None:
            msg = "Database not created yet. Call create_database() first."
            raise RuntimeError(msg)

        # Create a new connection each time to avoid threading issues
        return duckdb.connect(str(self._db_path))

    def close(self) -> None:
        """Close any open database connections.

        This method ensures clean shutdown of database resources.
        """
        if self._connection is not None:
            try:
                self._connection.close()
                self._connection = None
            except Exception as e:
                logger = logging.getLogger(__name__)
                app_logger = AppLoggerAdapter(logger, operation="DATABASE_CLEANUP")
                app_logger.warning(f"Error closing database connection: {e}")

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: object | None
    ) -> None:
        """Context manager exit - ensures database cleanup."""
        self.close()
