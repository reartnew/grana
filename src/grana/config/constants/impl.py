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
    "RcFile",
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

    ENVIRONMENT_VARIABLE_NAME = "GRANA_LOG_LEVEL"
    DEFAULT = "ERROR"

    def from_cli_arg(self) -> str:
        raw_log_level: str = self._get_cli_arg("log_level")
        _log_levels_normalization_map: dict[str, str] = {
            "0": "ERROR",
            "1": "WARNING",
            "2": "INFO",
            "3": "DEBUG",
        }
        return _log_levels_normalization_map.get(raw_log_level, raw_log_level)

    def from_rc_file(self) -> str:
        return self._get_rc_value("log_level")


class LogFile(base.ConstantBase[t.Optional[Path]]):
    """Log file constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_LOG_FILE"
    DEFAULT = None

    def from_rc_file(self) -> Path:
        return Path(self._get_rc_value("log_file"))


class RcFile(base.ConstantBase[Path]):
    """Runtime configuration file constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_RC_FILE"

    def cast(self, value: str) -> Path:
        return Path(value)

    def default(self) -> Path:
        return Path().resolve() / ".granarc"


class ContextDirectory(base.ConstantBase[Path]):
    """Context directory constant"""

    def default(self) -> Path:
        return Path().resolve()


class InteractiveMode(base.ConstantBase[bool]):
    """Interactive mode constant"""

    DEFAULT = False

    def from_cli_arg(self) -> bool:
        return self._get_cli_arg("interactive")


class WorkflowSourceFile(base.ConstantBase[t.Optional[Path]]):
    """Workflow source file constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_WORKFLOW_FILE"
    DEFAULT = None

    def cast(self, value: str) -> Path:
        return Path(value)

    def from_rc_file(self) -> Path:
        return Path(self._get_rc_value("workflow_file"))

    def from_cli_arg(self) -> Path:
        return Path(self._get_cli_arg("workflow_file"))


class WorkflowLoaderClass(base.ConstantBase[t.Optional[LoaderClassType]]):
    """Workflow loader class constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_WORKFLOW_LOADER_SOURCE_FILE"
    DEFAULT = None

    def cast(self, value: str) -> LoaderClassType:
        return t.cast(
            LoaderClassType,
            class_from_module(
                source_path=Path(value),
                class_name="WorkflowLoader",
                submodule_name="workflow.loader",
            ),
        )

    def from_rc_file(self) -> LoaderClassType:
        return self.cast(self._get_rc_value("workflow_loader_source_file"))


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

    def _load_from_source_file_or_by_name(
        self,
        display_source_file_getter: t.Callable[[], str],
        display_name_getter: t.Callable[[], str],
    ) -> DisplayClassType:
        try:
            custom_display_source_file: str = display_source_file_getter()
        except base.Inapplicable:
            known_display_name: str = display_name_getter()
            return self._display_class_by_name(known_display_name)
        return t.cast(
            DisplayClassType,
            class_from_module(
                source_path=Path(custom_display_source_file),
                class_name="Display",
                submodule_name="display",
            ),
        )

    def from_rc_file(self) -> DisplayClassType:
        return self._load_from_source_file_or_by_name(
            display_source_file_getter=lambda: self._get_rc_value("display_source_file"),
            display_name_getter=lambda: self._get_rc_value("display_name"),
        )

    def from_env(self) -> DisplayClassType:
        return self._load_from_source_file_or_by_name(
            display_source_file_getter=lambda: self._get_env("GRANA_DISPLAY_SOURCE_FILE"),
            display_name_getter=lambda: self._get_env("GRANA_DISPLAY_NAME"),
        )

    def default(self) -> DisplayClassType:
        from ...display.default import DefaultDisplay

        return DefaultDisplay


class StrategyClass(base.ConstantBase[StrategyClassType]):
    """Strategy class constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_STRATEGY_NAME"

    def cast(self, value: str) -> StrategyClassType:
        from ...strategy import KNOWN_STRATEGIES

        try:
            return KNOWN_STRATEGIES[value]
        except KeyError:
            raise ValueError(f"Invalid strategy name: {value!r} (allowed: {sorted(KNOWN_STRATEGIES)})") from None

    def from_cli_arg(self) -> StrategyClassType:
        strategy_name: str = self._get_cli_arg("strategy")
        return self.cast(strategy_name)

    def from_rc_file(self) -> StrategyClassType:
        strategy_name: str = self._get_rc_value("strategy")
        return self.cast(strategy_name)

    def from_workflow_configuration(self) -> StrategyClassType:
        strategy_name: str = self._get_wf_config_value("strategy")
        return self.cast(strategy_name)

    def default(self) -> StrategyClassType:
        from ...strategy import ExplicitStrategy

        return ExplicitStrategy


class UseColor(base.ConstantBase[bool]):
    """Use color constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_FORCE_COLOR"

    def cast(self, value: t.Union[str, bool]) -> bool:
        if isinstance(value, str):
            return self._string_to_bool(value)
        return value

    def from_rc_file(self) -> bool:
        return self._get_rc_value("force_color")

    def default(self) -> bool:
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutable(base.ConstantBase[str]):
    """Default shell executable constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_DEFAULT_SHELL_EXECUTABLE"
    DEFAULT = "/bin/sh"

    def from_rc_file(self) -> str:
        return self._get_rc_value("default_shell_executable")


class ShellInjectYieldFunction(base.ConstantBase[bool]):
    """Shell inject yield function constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_SHELL_INJECT_YIELD_FUNCTION"
    DEFAULT = True

    def cast(self, value: t.Union[str, bool]) -> bool:
        if isinstance(value, str):
            return self._string_to_bool(value)
        return value

    def from_rc_file(self) -> bool:
        return self._get_rc_value("shell_inject_yield_function")


class StrictOutcomesRendering(base.ConstantBase[bool]):
    """Strict outcomes rendering constant"""

    ENVIRONMENT_VARIABLE_NAME = "STRICT_OUTCOMES_RENDERING"
    DEFAULT = True

    def cast(self, value: t.Union[str, bool]) -> bool:
        if isinstance(value, str):
            return self._string_to_bool(value)
        return value

    def from_rc_file(self) -> bool:
        return self._get_rc_value("strict_outcomes_rendering")


class ActionClassDirectories(base.ConstantBase[list[Path]]):
    """Action class directories constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY"
    DEFAULT = []

    def cast(self, value: t.Union[str, list[Path]]) -> list[Path]:
        if isinstance(value, str):
            return self._string_to_path_list(value)
        return value

    def from_rc_file(self) -> list[Path]:
        return self._get_rc_value("action_classes_directories")


class ExternalPythonModulesPaths(base.ConstantBase[list[Path]]):
    """External python module paths constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_EXTERNAL_MODULES_PATHS"
    DEFAULT = []

    def cast(self, value: t.Union[str, list[Path]]) -> list[Path]:
        if isinstance(value, str):
            return self._string_to_path_list(value)
        return value

    def from_rc_file(self) -> list[Path]:
        return self._get_rc_value("external_python_modules_paths")
