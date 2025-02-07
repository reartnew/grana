# pylint: disable=import-outside-toplevel,cyclic-import
"""Lazy-loaded constants"""

import enum
import functools
import os
import sys
import typing as t
from io import UnsupportedOperation
from pathlib import Path

from .cli import get_cli_arg
from .helpers import class_from_module
from ...logging import WithLogger
from ...tools.inspect import get_class_annotations
from ...types import (
    LoaderClassType,
    StrategyClassType,
    DisplayClassType,
)

__all__ = [
    "C",
    "LOG_LEVELS",
    "Constant",
    "ConstantSource",
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


class ConstantValueInfo(t.NamedTuple):
    """Constants value information"""

    name: str
    value: str
    effective_source: ConstantSource


class Constant(WithLogger, t.Generic[VT]):
    """Constants used in grana runtime"""

    @classmethod
    def cache_clear(cls) -> None:
        """Reset cache"""
        cls._get.cache_clear()

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

    def _get_cli_arg(self, name: str) -> t.Any:
        if (value := get_cli_arg(name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined CLI argument {name!r} is accessed by {self._name!r}")
        return value

    def _get_env(self, name: str) -> str:
        if (value := os.environ.get(name)) is None:
            raise Inapplicable
        self.logger.debug(f"Defined environment variable {name!r} is accessed by {self._name!r}")
        return value

    @classmethod
    def _string_to_bool(cls, value: str) -> bool:
        """Converts a string value to a boolean"""
        if value == "Y":
            return True
        if value == "N":
            return False
        if value == "":
            raise Inapplicable
        raise ValueError(f"{value!r} is not a valid value for a boolean variable. Expected one of: 'Y', 'N'.")

    @classmethod
    def _string_to_path_list(cls, value: str) -> list[Path]:
        return [Path(item.strip()) for item in value.split(":") if item]

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


class EnvFileConstant(Constant[Path]):
    """Environment variables file constant"""

    def from_env(self) -> Path:
        return Path(self._get_env("GRANA_ENV_FILE"))

    def default(self) -> Path:
        return Path().resolve() / ".env"


class ContextDirectoryConstant(Constant[Path]):
    """Context directory constant"""

    def default(self) -> Path:
        return Path().resolve()


class InteractiveModeConstant(Constant[bool]):
    """Interactive mode constant"""

    def from_cli_arg(self) -> bool:
        return self._get_cli_arg("interactive")

    def default(self) -> bool:
        return False


class WorkflowSourceFileConstant(Constant[t.Optional[Path]]):
    """Workflow source file constant"""

    def from_env(self) -> Path:
        return Path(self._get_env("GRANA_WORKFLOW_FILE"))

    def from_cli_arg(self) -> Path:
        return Path(self._get_cli_arg("workflow_file"))

    def default(self) -> None:
        return None


class WorkflowLoaderClassConstant(Constant[t.Optional[LoaderClassType]]):
    """Workflow loader class constant"""

    def from_env(self) -> LoaderClassType:
        return t.cast(
            LoaderClassType,
            class_from_module(
                source_path=Path(self._get_env("GRANA_WORKFLOW_LOADER_SOURCE_FILE")),
                class_name="WorkflowLoader",
                submodule_name="workflow.loader",
            ),
        )

    def default(self) -> None:
        return None


class DisplayClassConstant(Constant[DisplayClassType]):
    """Display class constant"""

    @classmethod
    def _display_class_by_name(cls, name: str) -> DisplayClassType:
        from ...display.default import KNOWN_DISPLAYS

        try:
            return KNOWN_DISPLAYS[name]
        except Exception:
            raise ValueError(f"Display name should be one of: {sorted(KNOWN_DISPLAYS)}. Got {name!r}") from None

    def from_cli_arg(self) -> DisplayClassType:
        display_name: str = self._get_cli_arg("display")
        return self._display_class_by_name(display_name)

    def from_env(self) -> DisplayClassType:
        try:
            custom_display_source_file: str = self._get_env("GRANA_DISPLAY_SOURCE_FILE")
        except Inapplicable:
            known_display_name: str = self._get_env("GRANA_DISPLAY_NAME")
            return self._display_class_by_name(known_display_name)
        return t.cast(
            DisplayClassType,
            class_from_module(
                source_path=Path(custom_display_source_file),
                class_name="Display",
                submodule_name="display",
            ),
        )

    def default(self) -> DisplayClassType:
        from ...display.default import DefaultDisplay

        return DefaultDisplay


class StrategyClassConstant(Constant[StrategyClassType]):
    """Strategy class constant"""

    @classmethod
    def _strategy_class_by_name(cls, name: str) -> StrategyClassType:
        from ...strategy import KNOWN_STRATEGIES

        try:
            return KNOWN_STRATEGIES[name]
        except KeyError:
            raise ValueError(f"Invalid strategy name: {name!r} (allowed: {sorted(KNOWN_STRATEGIES)})") from None

    def from_cli_arg(self) -> StrategyClassType:
        strategy_name: str = self._get_cli_arg("strategy")
        return self._strategy_class_by_name(strategy_name)

    def from_env(self) -> StrategyClassType:
        strategy_name: str = self._get_env("GRANA_STRATEGY_NAME")
        return self._strategy_class_by_name(strategy_name)

    def default(self) -> StrategyClassType:
        from ...strategy import ExplicitStrategy

        return ExplicitStrategy


class UseColorConstant(Constant[bool]):
    """Use color constant"""

    def from_env(self) -> bool:
        force_color: str = self._get_env("GRANA_FORCE_COLOR")
        return self._string_to_bool(force_color)

    def default(self) -> bool:
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutableConstant(Constant[str]):
    """Default shell executable constant"""

    def from_env(self) -> str:
        return self._get_env("GRANA_DEFAULT_SHELL_EXECUTABLE")

    def default(self) -> str:
        return "/bin/sh"


class ShellInjectYieldFunctionConstant(Constant[bool]):
    """Shell inject yield function constant"""

    def from_env(self) -> bool:
        return self._string_to_bool(self._get_env("GRANA_SHELL_INJECT_YIELD_FUNCTION"))

    def default(self) -> bool:
        return True


class StrictOutcomesRenderingConstant(Constant[bool]):
    """Strict outcomes rendering constant"""

    def from_env(self) -> bool:
        return self._string_to_bool(self._get_env("STRICT_OUTCOMES_RENDERING"))

    def default(self) -> bool:
        return True


class ActionClassDirectoriesConstant(Constant[list[Path]]):
    """Action class directories constant"""

    def from_env(self) -> list[Path]:
        return self._string_to_path_list(self._get_env("GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY"))

    def default(self) -> list[Path]:
        return []


class ExternalPythonModulesPathsConstant(Constant[list[Path]]):
    """External python module paths constant"""

    def from_env(self) -> list[Path]:
        return self._string_to_path_list(self._get_env("GRANA_EXTERNAL_MODULES_PATHS"))

    def default(self) -> list[Path]:
        return []


class C:
    """Runtime constants"""

    LOG_LEVEL: Constant = LogLevelConstant()
    LOG_FILE: Constant = LogFileConstant()
    ENV_FILE: Constant = EnvFileConstant()
    CONTEXT_DIRECTORY: Constant = ContextDirectoryConstant()
    INTERACTIVE_MODE: Constant = InteractiveModeConstant()
    WORKFLOW_SOURCE_FILE: Constant = WorkflowSourceFileConstant()
    WORKFLOW_LOADER_CLASS: Constant = WorkflowLoaderClassConstant()
    DISPLAY_CLASS: Constant = DisplayClassConstant()
    STRATEGY_CLASS: Constant = StrategyClassConstant()
    USE_COLOR: Constant = UseColorConstant()
    DEFAULT_SHELL_EXECUTABLE: Constant = DefaultShellExecutableConstant()
    SHELL_INJECT_YIELD_FUNCTION: Constant = ShellInjectYieldFunctionConstant()
    STRICT_OUTCOMES_RENDERING: Constant = StrictOutcomesRenderingConstant()
    ACTION_CLASSES_DIRECTORIES: Constant = ActionClassDirectoriesConstant()
    EXTERNAL_PYTHON_MODULES_PATHS: Constant = ExternalPythonModulesPathsConstant()

    @classmethod
    def info(cls) -> list[ConstantValueInfo]:
        """Return set of info for all constants"""
        result: list[ConstantValueInfo] = []
        for attr_name, attr_type in sorted(get_class_annotations(cls).items()):
            if not isinstance(attr_type, type) or not issubclass(attr_type, Constant):
                continue
            attr_value: t.Any = getattr(C, attr_name)
            attr_effective_source = _SOURCES[attr_name]
            result.append(ConstantValueInfo(attr_name, attr_value, attr_effective_source))
        return result
