"""
Provides a custom logger object.

Should be used like the following:

```
from cambrian.utils.logger import LOGGER

LOGGER.fatal("Fatal")
LOGGER.error("Error")
LOGGER.warn("Warning")
LOGGER.info("Information")
LOGGER.debug("Debug")
```
"""

import logging
import logging.config
from typing import Optional
import pathlib

from cambrian.utils.config import MjCambrianConfig


class MjCambrianTqdmStreamHandler(logging.StreamHandler):
    """A handler that uses tqdm.write to log messages."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            from tqdm import tqdm

            tqdm.write(msg, end=self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class MjCambrianLoggerMaxLevelFilter(logging.Filter):
    """This filter sets a maximum level."""

    def __init__(self, max_level: int = logging.INFO):
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= self.max_level


def get_logger(
    config: Optional[MjCambrianConfig] = None,
    *,
    name: str = "cambrian",
    overwrite_filepath: Optional[pathlib.Path] = None,
    overwrite_filename_suffix: Optional[str] = None,
    allow_missing_filepath: bool = True,
) -> logging.Logger:
    """Get/configure the logger."""
    if config is None:
        return logging.getLogger(name)

    # Walk through the handlers and remove any that don't have a valid filepath.
    for handler_name, handler in config.select("logging_config.handlers").items():
        filename = handler.get("filename", None)
        if not filename:
            continue

        filename = pathlib.Path(filename)
        if overwrite_filepath:
            filename = overwrite_filepath / filename.name
        if overwrite_filename_suffix:
            # The suffix will be added before the file extension.
            filename = filename.with_name(
                filename.stem + overwrite_filename_suffix + filename.suffix
            )

        if filename.parent.exists():
            config.logging_config["handlers"][handler_name]["filename"] = str(filename)
        elif allow_missing_filepath:
            # If the file doesn't exist, remove the handler from the config.
            del config.logging_config["handlers"][handler_name]
            for logger in config.logging_config["loggers"].values():
                logger["handlers"].remove(handler_name)
        else:
            raise FileNotFoundError(f"Directory {filename.parent} does not exist.")

    logging.config.dictConfig(config.logging_config)

    return logging.getLogger(name)