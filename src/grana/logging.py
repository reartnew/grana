"""It's all about logging."""

import functools
import logging
import logging.config
import pathlib
import sys
import typing as t

from .tools.context import ContextManagerVar

__all__ = [
    "WithLogger",
    "context",
    "configure_logging",
]


class LoggerProperty:
    """Class-level logger property"""

    @staticmethod
    @functools.cache
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

LOG_CONTEXT_DATA: ContextManagerVar[dict[str, t.Any]] = ContextManagerVar(default={})


class ContextFilter(logging.Filter):
    """Try filters"""

    def filter(self, record: logging.LogRecord) -> bool:
        if not (ctx := LOG_CONTEXT_DATA.get()):
            record.__dict__["context"] = ""
            return True
        ctx_pairs = (f"{k}={ctx[k]}" for k in sorted(ctx))
        record.__dict__["context"] = f" {{{', '.join(ctx_pairs)}}}"
        return True


def context(**kwargs):
    """Manager for log record context data"""
    return LOG_CONTEXT_DATA.set(kwargs)


class MonochromeFormatter(logging.Formatter):
    """No colors"""

    def __init__(self):
        super().__init__(fmt="{asctime} {levelname} [{name}]{context} {message}", style="{")


class ColorFormatter(logging.Formatter):
    """With colors in the level name"""

    def __init__(self):
        super().__init__(fmt="{asctime} {colored_levelname} [{name}]{colored_context} {message}", style="{")

    def format(self, record: logging.LogRecord) -> str:
        record.__dict__["colored_levelname"] = self._colorize_level_name(record.levelname)
        colored_context: str = ""
        if ctx := record.__dict__.get("context", ""):
            colored_context = self._colorize_string_by_code(ctx, 37)  # Gray
        record.__dict__["colored_context"] = colored_context
        return super().format(record)

    @classmethod
    @functools.cache
    def _colorize_level_name(cls, name: str) -> str:
        code: int = COLOR_CODE_MAP.get(name, DEFAULT_COLOR_CODE)
        return cls._colorize_string_by_code(name, code)

    @classmethod
    def _colorize_string_by_code(cls, string: str, code: int) -> str:
        return f"\033[{code}m{string}\033[0m"


def get_main_logger() -> logging.Logger:
    """Return the root logger for the package"""
    # Trim subpackage name
    root_logger_name: str = __name__.removesuffix(".logging")
    return logging.getLogger(root_logger_name)


def configure_logging(level: str, colorize: bool = False, main_file: t.Optional[pathlib.Path] = None) -> None:
    """Logging setup"""
    main_logger = get_main_logger()
    main_logger.setLevel(level)
    ctx_filter = ContextFilter()

    if not main_file:
        # Process stdout handler
        stderr_handler = logging.StreamHandler(sys.stderr)
        formatter: logging.Formatter = ColorFormatter() if colorize else MonochromeFormatter()
        stderr_handler.setFormatter(formatter)
        stderr_handler.addFilter(ctx_filter)
        main_logger.addHandler(stderr_handler)
    else:
        # Process file handler
        filename = main_file.expanduser().resolve()
        # Prepare parent directory
        filename.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(filename, mode="w")
        file_handler.setFormatter(MonochromeFormatter())
        file_handler.addFilter(ctx_filter)
        main_logger.addHandler(file_handler)
