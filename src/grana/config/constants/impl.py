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
    "InternalDisplayClass",
    "ExternalDisplayClass",
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
    COMMAND_LINE_OPTION_NAME = "log_level"
    RC_PARAMETER_NAME = "log_level"
    DEFAULT = "ERROR"

    _LOG_LEVELS_NORMALIZATION_MAP: dict[str, str] = {
        "0": "ERROR",
        "1": "WARNING",
        "2": "INFO",
        "3": "DEBUG",
    }

    def cast(self, value: t.Any) -> str:
        return self._LOG_LEVELS_NORMALIZATION_MAP.get(value, value)


class LogFile(base.ConstantBase[t.Optional[Path]]):
    """Log file constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_LOG_FILE"
    RC_PARAMETER_NAME = "log_file"
    DEFAULT = None


class RcFile(base.ConstantPath[Path]):
    """Runtime configuration file constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_RC_FILE"

    def default(self) -> Path:
        return Path().resolve() / ".granarc"


class ContextDirectory(base.ConstantPath[Path]):
    """Context directory constant"""

    def default(self) -> Path:
        return Path().resolve()


class InteractiveMode(base.ConstantBool):
    """Interactive mode constant"""

    COMMAND_LINE_OPTION_NAME = "interactive"
    DEFAULT = False


class WorkflowSourceFile(base.ConstantPath[t.Optional[Path]]):
    """Workflow source file constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_WORKFLOW_FILE"
    COMMAND_LINE_OPTION_NAME = "workflow_file"
    RC_PARAMETER_NAME = "workflow_file"
    DEFAULT = None


class WorkflowLoaderClass(base.ConstantBase[t.Optional[LoaderClassType]]):
    """Workflow loader class constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_WORKFLOW_LOADER_SOURCE_FILE"
    RC_PARAMETER_NAME = "workflow_loader_source_file"
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


class InternalDisplayClass(base.ConstantBase[DisplayClassType]):
    """Display class constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_DISPLAY_NAME"
    RC_PARAMETER_NAME = "display_name"
    COMMAND_LINE_OPTION_NAME = "display"

    def cast(self, value: str) -> DisplayClassType:
        from ...display.default import KNOWN_DISPLAYS

        try:
            return KNOWN_DISPLAYS[value]
        except Exception:
            raise ValueError(f"Display name should be one of: {sorted(KNOWN_DISPLAYS)}. Got {value!r}") from None

    def default(self) -> DisplayClassType:
        from ...display.default import DefaultDisplay

        return DefaultDisplay


class ExternalDisplayClass(base.ConstantBase[t.Optional[DisplayClassType]]):
    """Display class constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_DISPLAY_SOURCE_FILE"
    RC_PARAMETER_NAME = "display_source_file"
    DEFAULT = None

    def cast(self, value: str) -> DisplayClassType:
        return t.cast(
            DisplayClassType,
            class_from_module(
                source_path=Path(value),
                class_name="Display",
                submodule_name="display",
            ),
        )


class StrategyClass(base.ConstantBase[StrategyClassType]):
    """Strategy class constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_STRATEGY_NAME"
    COMMAND_LINE_OPTION_NAME = "strategy"
    WORKFLOW_CONFIG_PARAMETER_NAME = "strategy"
    RC_PARAMETER_NAME = "strategy"

    def cast(self, value: str) -> StrategyClassType:
        from ...strategy import KNOWN_STRATEGIES

        try:
            return KNOWN_STRATEGIES[value]
        except KeyError:
            raise ValueError(f"Invalid strategy name: {value!r} (allowed: {sorted(KNOWN_STRATEGIES)})") from None

    def default(self) -> StrategyClassType:
        from ...strategy import ExplicitStrategy

        return ExplicitStrategy


class UseColor(base.ConstantBool):
    """Use color constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_FORCE_COLOR"
    RC_PARAMETER_NAME = "force_color"

    def default(self) -> bool:
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutable(base.ConstantBase[str]):
    """Default shell executable constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_DEFAULT_SHELL_EXECUTABLE"
    RC_PARAMETER_NAME = "default_shell_executable"
    DEFAULT = "/bin/sh"


class ShellInjectYieldFunction(base.ConstantBool):
    """Shell inject yield function constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_SHELL_INJECT_YIELD_FUNCTION"
    RC_PARAMETER_NAME = "shell_inject_yield_function"
    DEFAULT = True


class StrictOutcomesRendering(base.ConstantBool):
    """Strict outcomes rendering constant"""

    ENVIRONMENT_VARIABLE_NAME = "STRICT_OUTCOMES_RENDERING"
    RC_PARAMETER_NAME = "strict_outcomes_rendering"
    DEFAULT = True


class ActionClassDirectories(base.ConstantPathList):
    """Action class directories constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY"
    RC_PARAMETER_NAME = "action_classes_directories"
    DEFAULT = []


class ExternalPythonModulesPaths(base.ConstantPathList):
    """External python module paths constant"""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_EXTERNAL_MODULES_PATHS"
    RC_PARAMETER_NAME = "external_python_modules_paths"
    DEFAULT = []
