"""It's all about logging."""

import functools
import logging
import logging.config
import pathlib
import sys
import typing as t

__all__ = [
    "WithLogger",
    "configure_logging",
]


class LoggerProperty:
    """Class-level logger property"""

    @staticmethod
    @functools.lru_cache(None)
    def _prepare(caller_type: type) -> logging.Logger:
        return logging.getLogger(f"{caller_type.__module__}.{caller_type.__name__}")

    def __get__(self, caller_instance: t.Any, caller_type: type) -> logging.Logger:
        return self._prepare(caller_type)


class WithLogger:
    """Add logger property"""

    logger = LoggerProperty()


COLOR_CODE_MAP: dict[str, int] = {
    "CRITICAL": 31,
    "FATAL": 31,
    "ERROR": 31,
    "WARN": 35,
    "WARNING": 35,
    "INFO": 34,
    "DEBUG": 32,
    "NOTSET": 37,
    "TRACE": 33,
}
DEFAULT_COLOR_CODE: int = 37


class MonochromeFormatter(logging.Formatter):
    """No colors"""

    def __init__(self):
        super().__init__(fmt="{asctime} {levelname} [{name}] {message}", style="{")


class ColorFormatter(logging.Formatter):
    """With colors in the level name"""

    def __init__(self):
        super().__init__(fmt="{asctime} {colored_level_name} [{name}] {message}", style="{")

    def format(self, record: logging.LogRecord) -> str:
        record.__dict__["colored_level_name"] = self._colorize_level_name(record.levelname)
        return super().format(record)

    @classmethod
    @functools.lru_cache(10)
    def _colorize_level_name(cls, name: str) -> str:
        code: int = COLOR_CODE_MAP.get(name, DEFAULT_COLOR_CODE)
        return f"\033[{code}m{name}\033[0m"


def configure_logging(level: str, colorize: bool = False, main_file: t.Optional[pathlib.Path] = None) -> None:
    """Logging setup"""
    main_logger = logging.getLogger("grana")
    main_logger.setLevel(level)

    if main_file is None:
        # Process stdout handler
        stderr_handler = logging.StreamHandler(sys.stderr)
        formatter: logging.Formatter = ColorFormatter() if colorize else MonochromeFormatter()
        stderr_handler.setFormatter(formatter)
        main_logger.addHandler(stderr_handler)
    else:
        # Process file handler
        filename = main_file.expanduser().resolve()
        # Prepare parent directory
        filename.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(filename, mode="w")
        file_handler.setFormatter(MonochromeFormatter())
        main_logger.addHandler(file_handler)
