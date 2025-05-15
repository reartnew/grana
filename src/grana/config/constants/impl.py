"""Lazy-loaded constants implementations"""

import os
import sys
import typing as t
from io import UnsupportedOperation
from pathlib import Path

from . import base
from .cli import get_cli_option
from .helpers import class_from_module
from ...strategy.base import BaseStrategy
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
    "DependencyDefaultStrictness",
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
    """Specifies the level for the logging subsystem."""

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
        allowed_log_levels: list[str] = list(log_levels_normalization_map.values()) + list(log_levels_normalization_map)
        if value not in allowed_log_levels:
            raise ValueError(f"{value!r} is not a valid log level (expected one of: {allowed_log_levels})")
        return log_levels_normalization_map.get(value, value)


class LogFile(base.ConstantPath[t.Optional[Path]]):
    """Specifies the log file path."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_LOG_FILE"
    COMMAND_LINE_OPTION_NAME = "log_file"
    RC_PARAMETER_NAME = "log_file"
    DEFAULT = None


class RcFile(base.ConstantPath[Path]):
    """Specifies the runtime configuration file location."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_RC_FILE"

    def default(self) -> Path:
        """`.granarc` file in the current working directory"""
        return Path().resolve() / ".granarc"


class ContextDirectory(base.ConstantPath[Path]):
    """A directory that is used to resolve all relative paths."""

    def default(self) -> Path:
        """Current working directory"""
        return Path().resolve()


class InteractiveMode(base.ConstantBool):
    """Specifies whither to run plan interaction phase or not."""

    COMMAND_LINE_OPTION_NAME = "interactive"
    DEFAULT = False


class DependencyDefaultStrictness(base.ConstantBool):
    """Default strictness for action dependencies."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_STRICT_DEPENDENCIES"
    RC_PARAMETER_NAME = "strict"
    WORKFLOW_CONFIG_PARAMETER_NAME = "strict"
    DEFAULT = False


class WorkflowSourceFile(base.ConstantPath[t.Optional[Path]]):
    """Workflow source file path.
    When not set, `grana.yml`/`grana.yaml` are being looked for in the working directory.
    If set to `-`, then standard input stream is used as the source."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_WORKFLOW_FILE"
    RC_PARAMETER_NAME = "workflow_file"
    DEFAULT = None

    def from_cli_option(self) -> t.Optional[Path]:
        """Positional argument to `grana run` and `grana validate`."""
        cli_arg_name: str = "workflow_file"
        if (cli_arg_value := get_cli_option(cli_arg_name)) is None:
            raise base.Inapplicable
        self.logger.debug(f"Defined CLI positional argument {cli_arg_name!r} is accessed by {self._name!r}")
        return self.cast(cli_arg_value)


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
    """Selects a display by name from the bundled list."""

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
        """`prefix`"""
        from ...display.default import PrefixDisplay

        return PrefixDisplay


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
    """Specifies the execution strategy."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_STRATEGY_NAME"
    COMMAND_LINE_OPTION_NAME = "strategy"
    WORKFLOW_CONFIG_PARAMETER_NAME = "strategy"
    RC_PARAMETER_NAME = "strategy"

    def cast(self, value: str) -> StrategyClassType:
        return BaseStrategy.get_strategy_class_by_name(value)

    def default(self) -> StrategyClassType:
        """`auto`"""
        from ...strategy.impl import AutoStrategy

        return AutoStrategy


class UseColor(base.ConstantBool):
    """When specified, this will force the colored or non-colored output, according to the setting."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_FORCE_COLOR"
    RC_PARAMETER_NAME = "force_color"

    def default(self) -> bool:
        """Depending on if a TTY is allocated."""
        try:
            return os.isatty(sys.stdout.fileno())
        except UnsupportedOperation:
            return False


class DefaultShellExecutable(base.ConstantBase[str]):
    """Specifies which shell executable should be used by the shell action by default."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_DEFAULT_SHELL_EXECUTABLE"
    RC_PARAMETER_NAME = "default_shell_executable"
    WORKFLOW_CONFIG_PARAMETER_NAME = "default_shell_executable"
    DEFAULT = "/bin/sh"


class ShellInjectYieldFunction(base.ConstantBool):
    """When set to True, all shell-related actions will inject the yield_outcome function definition."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_SHELL_INJECT_YIELD_FUNCTION"
    RC_PARAMETER_NAME = "shell_inject_yield_function"
    WORKFLOW_CONFIG_PARAMETER_NAME = "shell_inject_yield_function"
    DEFAULT = True


class StrictOutcomesRendering(base.ConstantBool):
    """When set to True, rendering a missing outcome key will result in an error instead of an empty string."""

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


class ExternalPythonModulesPaths(base.ConstantPathList):
    """A list of local directories, which are added to the sys.path while loading any external modules."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_EXTERNAL_MODULES_PATHS"
    RC_PARAMETER_NAME = "external_python_modules_paths"
    WORKFLOW_CONFIG_PARAMETER_NAME = "external_python_modules_paths"


class SubprocessStreamBufferLimit(base.ConstantBase[int]):
    """An integer number defining the maximum line stdout/stderr length for a spawned subprocess."""

    ENVIRONMENT_VARIABLE_NAME = "GRANA_SUBPROCESS_STREAM_BUFFER_LIMIT"
    RC_PARAMETER_NAME = "subprocess_stream_buffer_limit"
    DEFAULT = 2**16  # asyncio.streams._DEFAULT_LIMIT

    def cast(self, value: t.Any) -> int:
        return int(value)
