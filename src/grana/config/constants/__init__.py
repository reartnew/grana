# pylint: disable=import-outside-toplevel,cyclic-import
"""Lazy-loaded constants"""
import enum
import functools
import os
import sys
import typing as t
from io import UnsupportedOperation
from pathlib import Path

from . import environment
from .cli import get_cli_arg
from .helpers import (
    Optional,
    Mandatory,
    maybe_path,
    maybe_class_from_module,
)
from ...logging import WithLogger
from ...types import (
    LoaderClassType,
    StrategyClassType,
    DisplayClassType,
)

__all__ = [
    "C",
    "LOG_LEVELS",
    "Constant",
    "get_constant_value_and_effective_source",
]

LOG_LEVELS: dict[str, str] = {
    "0": "ERROR",
    "1": "WARNING",
    "2": "INFO",
    "3": "DEBUG",
    "ERROR": "ERROR",
    "WARNING": "WARNING",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
}


def _maybe_strategy(name: t.Optional[str]) -> t.Optional[StrategyClassType]:
    """Transform an optional strategy name into an optional strategy class"""
    from ...strategy import KNOWN_STRATEGIES

    try:
        return KNOWN_STRATEGIES[name] if name else None
    except KeyError:
        raise ValueError(f"Invalid strategy name: {name!r} (allowed: {sorted(KNOWN_STRATEGIES)})") from None


def _maybe_display_class_by_name(name: t.Optional[str]) -> t.Optional[DisplayClassType]:
    from ...display.default import KNOWN_DISPLAYS

    if not name:
        return None
    try:
        return KNOWN_DISPLAYS[name]
    except Exception:
        raise ValueError(f"Display name should be one of: {sorted(KNOWN_DISPLAYS)}. Got {name!r}") from None


def _get_default_display_class() -> DisplayClassType:
    from ...display.default import DefaultDisplay

    return DefaultDisplay


def _get_strategy_class_from_cli_arg() -> t.Optional[StrategyClassType]:
    from ...strategy import KNOWN_STRATEGIES

    return _maybe_strategy(get_cli_arg("strategy", valid_options=KNOWN_STRATEGIES))


def _get_default_strategy_class() -> StrategyClassType:
    from ...strategy import ExplicitStrategy

    return ExplicitStrategy


def _isatty() -> bool:
    try:
        return os.isatty(sys.stdout.fileno())
    except UnsupportedOperation:
        return False


VT = t.TypeVar("VT")


class Inapplicable(BaseException):
    """Used to indicate that the source can not be used"""


class ConstantSource(enum.Enum):
    """Enumeration of constant effective value sources"""

    COMMAND = "CLI argument"
    ENVIRONMENT = "environment variable"
    DEFAULT = "default value"


_SOURCES: dict[str, ConstantSource] = {}


def get_constant_value_and_effective_source(name: str) -> tuple[t.Any, ConstantSource]:
    """Obtains the value and its effective source"""
    value: t.Any = getattr(C, name)
    return value, _SOURCES[name]


class Constant(WithLogger, t.Generic[VT]):
    """Constants used in grana runtime"""

    def __init__(self) -> None:
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    # Indefinite cache size, so all constants fit into it
    # pylint: disable=method-cache-max-size-none
    @functools.lru_cache(None)
    def _get(self) -> VT:
        for source, method in (
            (ConstantSource.COMMAND, self.from_cli_arg),
            (ConstantSource.ENVIRONMENT, self.from_env),
            (ConstantSource.DEFAULT, self.default),
        ):
            try:
                result = method()
            except Inapplicable:
                pass
            else:
                self.logger.debug(f"Effective value for {self._name!r} is {result!r} (from {source.value})")
                _SOURCES[self._name] = source
                return result
        raise NotImplementedError

    def __get__(self, instance: t.Any, owner: type) -> VT:
        return self._get()

    def _get_cli_arg(self, name: str) -> str:
        if (value := get_cli_arg(name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined CLI argument {name!r} is accessed by {self._name!r}")
        return value

    def _get_env(self, name: str) -> str:
        if (value := os.environ.get(name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined environment variable {name!r} is accessed by {self._name!r}")
        return value

    def from_env(self) -> VT:
        """Try to load the value from environment variables"""
        raise Inapplicable

    def from_cli_arg(self) -> VT:
        """Try to load the value from CLI args"""
        raise Inapplicable

    def default(self) -> VT:
        """Default value to be applied after every other source has been tested"""
        raise Inapplicable


class LogLevelConstant(Constant[str]):
    """Log level constant"""

    def from_cli_arg(self) -> str:
        raw_log_level: str = self._get_cli_arg("log_level")
        return LOG_LEVELS[raw_log_level]

    def from_env(self) -> str:
        return self._get_env("GRANA_LOG_LEVEL")

    def default(self) -> str:
        return "ERROR"


class LogFileConstant(Constant[t.Optional[Path]]):
    """Log file constant"""

    def from_env(self) -> Path:
        log_file_str: str = self._get_env("GRANA_LOG_FILE")
        return Path(log_file_str)

    def default(self) -> None:
        return None


class C:
    """Runtime constants"""

    LOG_LEVEL: Constant = LogLevelConstant()
    LOG_FILE: Constant = LogFileConstant()
    ENV_FILE: Mandatory[Path] = Mandatory(
        lambda: maybe_path(os.environ.get("GRANA_ENV_FILE")),
        lambda: Path().resolve() / ".env",
    )
    CONTEXT_DIRECTORY: Mandatory[Path] = Mandatory(
        lambda: Path().resolve(),
    )
    INTERACTIVE_MODE: Mandatory[bool] = Mandatory(
        lambda: get_cli_arg("interactive"),
        lambda: False,
    )
    ACTIONS_SOURCE_FILE: Optional[Path] = Optional(
        lambda: maybe_path(get_cli_arg("workflow_file")),
        lambda: maybe_path(os.environ.get("GRANA_WORKFLOW_FILE")),
    )
    WORKFLOW_LOADER_CLASS: Optional[LoaderClassType] = Optional(
        lambda: maybe_class_from_module(
            path_str=os.environ.get("GRANA_WORKFLOW_LOADER_SOURCE_FILE"),
            class_name="WorkflowLoader",
            submodule_name="workflow.loader",
        )
    )
    ACTION_CLASSES_DIRECTORIES: Mandatory[list[str]] = Mandatory(
        lambda: environment.to_path_list(os.environ.get("GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY", "")),
    )
    EXTERNAL_PYTHON_MODULES_PATHS: Mandatory[list[Path]] = Mandatory(
        lambda: environment.to_path_list(os.environ.get("GRANA_EXTERNAL_MODULES_PATHS", "")),
    )
    DISPLAY_CLASS: Mandatory[DisplayClassType] = Mandatory(
        lambda: _maybe_display_class_by_name(get_cli_arg("display")),
        lambda: maybe_class_from_module(
            path_str=os.environ.get("GRANA_DISPLAY_SOURCE_FILE"),
            class_name="Display",
            submodule_name="display",
        ),
        lambda: _maybe_display_class_by_name(os.environ.get("GRANA_DISPLAY_NAME")),
        _get_default_display_class,
    )
    STRATEGY_CLASS: Mandatory[StrategyClassType] = Mandatory(
        _get_strategy_class_from_cli_arg,
        lambda: _maybe_strategy(os.environ.get("GRANA_STRATEGY_NAME")),
        _get_default_strategy_class,
    )
    USE_COLOR: Mandatory[bool] = Mandatory(
        lambda: environment.to_ternary(os.environ.get("GRANA_FORCE_COLOR", "")),
        _isatty,
    )
    SHELL_INJECT_YIELD_FUNCTION: Mandatory[bool] = Mandatory(
        lambda: environment.to_bool(os.environ.get("GRANA_SHELL_INJECT_YIELD_FUNCTION", "Y")),
    )
    STRICT_OUTCOMES_RENDERING: Mandatory[bool] = Mandatory(
        lambda: environment.to_bool(os.environ.get("GRANA_STRICT_OUTCOMES_RENDERING", "Y")),
    )
    DEFAULT_SHELL_EXECUTABLE: Mandatory[str] = Mandatory(
        lambda: os.environ.get("GRANA_DEFAULT_SHELL_EXECUTABLE", "/bin/sh"),
    )
