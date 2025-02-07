# pylint: disable=import-outside-toplevel,cyclic-import
"""Lazy-loaded constants"""

import os
import sys
import typing as t
from io import UnsupportedOperation
from pathlib import Path

from . import base
from .cli import get_cli_arg
from .helpers import class_from_module
from ...tools.inspect import get_class_annotations
from ...types import (
    LoaderClassType,
    StrategyClassType,
    DisplayClassType,
)

__all__ = [
    "C",
    "LOG_LEVELS",
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


class LogLevelConstant(base.ConstantBase[str]):
    """Log level constant"""

    def from_cli_arg(self) -> str:
        raw_log_level: str = self._get_cli_arg("log_level")
        return LOG_LEVELS[raw_log_level]

    def from_env(self) -> str:
        return self._get_env("GRANA_LOG_LEVEL")

    def default(self) -> str:
        return "ERROR"


class LogFileConstant(base.ConstantBase[t.Optional[Path]]):
    """Log file constant"""

    def from_env(self) -> Path:
        log_file_str: str = self._get_env("GRANA_LOG_FILE")
        return Path(log_file_str)

    def default(self) -> None:
        return None


class EnvFileConstant(base.ConstantBase[Path]):
    """Environment variables file constant"""

    def from_env(self) -> Path:
        return Path(self._get_env("GRANA_ENV_FILE"))

    def default(self) -> Path:
        return Path().resolve() / ".env"


class ContextDirectoryConstant(base.ConstantBase[Path]):
    """Context directory constant"""

    def default(self) -> Path:
        return Path().resolve()


class InteractiveModeConstant(base.ConstantBase[bool]):
    """Interactive mode constant"""

    def from_cli_arg(self) -> bool:
        return self._get_cli_arg("interactive")

    def default(self) -> bool:
        return False


class WorkflowSourceFileConstant(base.ConstantBase[t.Optional[Path]]):
    """Workflow source file constant"""

    def from_env(self) -> Path:
        return Path(self._get_env("GRANA_WORKFLOW_FILE"))

    def from_cli_arg(self) -> Path:
        return Path(self._get_cli_arg("workflow_file"))

    def default(self) -> None:
        return None


class WorkflowLoaderClassConstant(base.ConstantBase[t.Optional[LoaderClassType]]):
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


class DisplayClassConstant(base.ConstantBase[DisplayClassType]):
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
        except base.Inapplicable:
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


class StrategyClassConstant(base.ConstantBase[StrategyClassType]):
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


class UseColorConstant(base.ConstantBase[bool]):
    """Use color constant"""

    def from_env(self) -> bool:
        force_color: str = self._get_env("GRANA_FORCE_COLOR")
        return self._string_to_bool(force_color)

    def default(self) -> bool:
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutableConstant(base.ConstantBase[str]):
    """Default shell executable constant"""

    def from_env(self) -> str:
        return self._get_env("GRANA_DEFAULT_SHELL_EXECUTABLE")

    def default(self) -> str:
        return "/bin/sh"


class ShellInjectYieldFunctionConstant(base.ConstantBase[bool]):
    """Shell inject yield function constant"""

    def from_env(self) -> bool:
        return self._string_to_bool(self._get_env("GRANA_SHELL_INJECT_YIELD_FUNCTION"))

    def default(self) -> bool:
        return True


class StrictOutcomesRenderingConstant(base.ConstantBase[bool]):
    """Strict outcomes rendering constant"""

    def from_env(self) -> bool:
        return self._string_to_bool(self._get_env("STRICT_OUTCOMES_RENDERING"))

    def default(self) -> bool:
        return True


class ActionClassDirectoriesConstant(base.ConstantBase[list[Path]]):
    """Action class directories constant"""

    def from_env(self) -> list[Path]:
        return self._string_to_path_list(self._get_env("GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY"))

    def default(self) -> list[Path]:
        return []


class ExternalPythonModulesPathsConstant(base.ConstantBase[list[Path]]):
    """External python module paths constant"""

    def from_env(self) -> list[Path]:
        return self._string_to_path_list(self._get_env("GRANA_EXTERNAL_MODULES_PATHS"))

    def default(self) -> list[Path]:
        return []


class C:
    """Runtime constants"""

    LOG_LEVEL: base.ConstantBase = LogLevelConstant()
    LOG_FILE: base.ConstantBase = LogFileConstant()
    ENV_FILE: base.ConstantBase = EnvFileConstant()
    CONTEXT_DIRECTORY: base.ConstantBase = ContextDirectoryConstant()
    INTERACTIVE_MODE: base.ConstantBase = InteractiveModeConstant()
    WORKFLOW_SOURCE_FILE: base.ConstantBase = WorkflowSourceFileConstant()
    WORKFLOW_LOADER_CLASS: base.ConstantBase = WorkflowLoaderClassConstant()
    DISPLAY_CLASS: base.ConstantBase = DisplayClassConstant()
    STRATEGY_CLASS: base.ConstantBase = StrategyClassConstant()
    USE_COLOR: base.ConstantBase = UseColorConstant()
    DEFAULT_SHELL_EXECUTABLE: base.ConstantBase = DefaultShellExecutableConstant()
    SHELL_INJECT_YIELD_FUNCTION: base.ConstantBase = ShellInjectYieldFunctionConstant()
    STRICT_OUTCOMES_RENDERING: base.ConstantBase = StrictOutcomesRenderingConstant()
    ACTION_CLASSES_DIRECTORIES: base.ConstantBase = ActionClassDirectoriesConstant()
    EXTERNAL_PYTHON_MODULES_PATHS: base.ConstantBase = ExternalPythonModulesPathsConstant()

    @classmethod
    def info(cls) -> list[base.ConstantValueInfo]:
        """Return set of info for all constants"""
        result: list[base.ConstantValueInfo] = []
        for attr_name, attr_type in sorted(get_class_annotations(cls).items()):
            if not isinstance(attr_type, type) or not issubclass(attr_type, base.ConstantBase):
                continue
            attr_value: t.Any = getattr(C, attr_name)
            attr_effective_source = base.CONSTANT_SOURCES[attr_name]
            result.append(base.ConstantValueInfo(attr_name, attr_value, attr_effective_source))
        return result
