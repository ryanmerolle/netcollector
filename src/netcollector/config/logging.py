"""Configuration models for logging."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, StrictBool

from netcollector.config.utils import get_cwd_file


class AppLoggingConfig(BaseModel):
    """Configuration for application logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    logfile: Path | None = get_cwd_file("./netcollector.log")
    stdout: StrictBool = True


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    main: AppLoggingConfig = AppLoggingConfig(level="INFO")
    scrapli: AppLoggingConfig = AppLoggingConfig(level="WARNING")
    pandas: AppLoggingConfig = AppLoggingConfig(level="WARNING")
