# pylint: disable=import-outside-toplevel,cyclic-import
"""Lazy-loaded constants implementations"""

import os
import sys
import typing as t
from io import UnsupportedOperation
from pathlib import Path

from . import base
from .helpers import class_from_module
from ...types import (
    LoaderClassType,
    StrategyClassType,
    DisplayClassType,
)

__all__ = [
    "LogLevel",
    "LogFile",
    "EnvFile",
    "ContextDirectory",
    "InteractiveMode",
    "WorkflowSourceFile",
    "WorkflowLoaderClass",
    "DisplayClass",
    "StrategyClass",
    "UseColor",
    "DefaultShellExecutable",
    "ShellInjectYieldFunction",
    "StrictOutcomesRendering",
    "ActionClassDirectories",
    "ExternalPythonModulesPaths",
]


class LogLevel(base.ConstantBase[str]):
    """Log level constant"""

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

    def from_cli_arg(self) -> str:
        raw_log_level: str = self._get_cli_arg("log_level")
        return self.LOG_LEVELS[raw_log_level]

    def from_env(self) -> str:
        return self._get_env("GRANA_LOG_LEVEL")

    def default(self) -> str:
        return "ERROR"


class LogFile(base.ConstantBase[t.Optional[Path]]):
    """Log file constant"""

    def from_env(self) -> Path:
        log_file_str: str = self._get_env("GRANA_LOG_FILE")
        return Path(log_file_str)

    def default(self) -> None:
        return None


class EnvFile(base.ConstantBase[Path]):
    """Environment variables file constant"""

    def from_env(self) -> Path:
        return Path(self._get_env("GRANA_ENV_FILE"))

    def default(self) -> Path:
        return Path().resolve() / ".env"


class ContextDirectory(base.ConstantBase[Path]):
    """Context directory constant"""

    def default(self) -> Path:
        return Path().resolve()


class InteractiveMode(base.ConstantBase[bool]):
    """Interactive mode constant"""

    def from_cli_arg(self) -> bool:
        return self._get_cli_arg("interactive")

    def default(self) -> bool:
        return False


class WorkflowSourceFile(base.ConstantBase[t.Optional[Path]]):
    """Workflow source file constant"""

    def from_env(self) -> Path:
        return Path(self._get_env("GRANA_WORKFLOW_FILE"))

    def from_cli_arg(self) -> Path:
        return Path(self._get_cli_arg("workflow_file"))

    def default(self) -> None:
        return None


class WorkflowLoaderClass(base.ConstantBase[t.Optional[LoaderClassType]]):
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


class DisplayClass(base.ConstantBase[DisplayClassType]):
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


class StrategyClass(base.ConstantBase[StrategyClassType]):
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


class UseColor(base.ConstantBase[bool]):
    """Use color constant"""

    def from_env(self) -> bool:
        force_color: str = self._get_env("GRANA_FORCE_COLOR")
        return self._string_to_bool(force_color)

    def default(self) -> bool:
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutable(base.ConstantBase[str]):
    """Default shell executable constant"""

    def from_env(self) -> str:
        return self._get_env("GRANA_DEFAULT_SHELL_EXECUTABLE")

    def default(self) -> str:
        return "/bin/sh"


class ShellInjectYieldFunction(base.ConstantBase[bool]):
    """Shell inject yield function constant"""

    def from_env(self) -> bool:
        return self._string_to_bool(self._get_env("GRANA_SHELL_INJECT_YIELD_FUNCTION"))

    def default(self) -> bool:
        return True


class StrictOutcomesRendering(base.ConstantBase[bool]):
    """Strict outcomes rendering constant"""

    def from_env(self) -> bool:
        return self._string_to_bool(self._get_env("STRICT_OUTCOMES_RENDERING"))

    def default(self) -> bool:
        return True


class ActionClassDirectories(base.ConstantBase[list[Path]]):
    """Action class directories constant"""

    def from_env(self) -> list[Path]:
        return self._string_to_path_list(self._get_env("GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY"))

    def default(self) -> list[Path]:
        return []


class ExternalPythonModulesPaths(base.ConstantBase[list[Path]]):
    """External python module paths constant"""

    def from_env(self) -> list[Path]:
        return self._string_to_path_list(self._get_env("GRANA_EXTERNAL_MODULES_PATHS"))

    def default(self) -> list[Path]:
        return []
