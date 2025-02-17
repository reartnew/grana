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
    """Specifies the log level.
    Default is ERROR."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_LOG_LEVEL"
    COMMAND_LINE_OPTION_NAME = "log_level"
    RC_PARAMETER_NAME = "log_level"
    DEFAULT = "ERROR"

    def cast(self, value: t.Any) -> str:
        log_levels_normalization_map: dict[str, str] = {
            "0": "ERROR",
            "1": "WARNING",
            "2": "INFO",
            "3": "DEBUG",
        }
        return log_levels_normalization_map.get(value, value)


class LogFile(base.ConstantPath[t.Optional[Path]]):
    """Specifies the log file.
    Defaults to the standard error stream."""

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
    """Workflow file to use.
    Default behaviour is to check the current working directory for a `grana.y[a]ml` file."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_WORKFLOW_FILE"
    COMMAND_LINE_OPTION_NAME = "workflow_file"
    RC_PARAMETER_NAME = "workflow_file"
    DEFAULT = None


class WorkflowLoaderClass(base.ConstantBase[t.Optional[LoaderClassType]]):
    """May point to a file containing a WorkflowLoader class definition,
    which will replace the default implementation."""

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
    """Select the display by name from the bundled list."""

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
    """May point to a file containing a Display class definition, which will replace the default implementation."""

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
    """Specifies the execution strategy.
    Default is 'explicit'."""

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
    """When specified, this will force the colored or non-colored output, according to the setting."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_FORCE_COLOR"
    RC_PARAMETER_NAME = "force_color"

    def default(self) -> bool:
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutable(base.ConstantBase[str]):
    """Specifies which shell executable should be used by the shell action by default.
    Default is /bin/sh."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_DEFAULT_SHELL_EXECUTABLE"
    RC_PARAMETER_NAME = "default_shell_executable"
    WORKFLOW_CONFIG_PARAMETER_NAME = "default_shell_executable"
    DEFAULT = "/bin/sh"


class ShellInjectYieldFunction(base.ConstantBool):
    """When set to True, all shell-related actions will inject the yield_outcome function definition.
    Default is True."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_SHELL_INJECT_YIELD_FUNCTION"
    RC_PARAMETER_NAME = "shell_inject_yield_function"
    WORKFLOW_CONFIG_PARAMETER_NAME = "shell_inject_yield_function"
    DEFAULT = True


class StrictOutcomesRendering(base.ConstantBool):
    """When set to True, rendering a missing outcome key will result in an error instead of an empty string.
    Default is False."""

    ENVIRONMENT_VARIABLE_NAME = "STRICT_OUTCOMES_RENDERING"
    RC_PARAMETER_NAME = "strict_outcomes_rendering"
    WORKFLOW_CONFIG_PARAMETER_NAME = "strict_outcomes_rendering"
    DEFAULT = True


class ActionClassDirectories(base.ConstantPathList):
    """A list of local directories, from which all `*.py` files will be considered action definitions.
    Each loaded definition is named after the filename stem and must contain an `Action` class.
    e.g. foo-bar.py may be referenced in a YAML workflow as `type: foo-bar`."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY"
    RC_PARAMETER_NAME = "action_classes_directories"
    WORKFLOW_CONFIG_PARAMETER_NAME = "action_classes_directories"
    DEFAULT = []


class ExternalPythonModulesPaths(base.ConstantPathList):
    """A list of local directories, which are added to the sys.path while loading any external modules.
    Default is an empty list."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_EXTERNAL_MODULES_PATHS"
    RC_PARAMETER_NAME = "external_python_modules_paths"
    WORKFLOW_CONFIG_PARAMETER_NAME = "external_python_modules_paths"
    DEFAULT = []
