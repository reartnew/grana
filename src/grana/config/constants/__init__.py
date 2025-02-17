"""Lazy-loaded constants"""

import typing as t

from . import base, impl
from .cli import get_cli_option
from .helpers import class_from_module
from ...tools.inspect import get_class_annotations

__all__ = [
    "C",
]


class C:
    """Runtime constants"""

    LOG_LEVEL: base.ConstantBase = impl.LogLevel()
    LOG_FILE: base.ConstantBase = impl.LogFile()
    RC_FILE: base.ConstantBase = impl.RcFile()
    CONTEXT_DIRECTORY: base.ConstantBase = impl.ContextDirectory()
    INTERACTIVE_MODE: base.ConstantBase = impl.InteractiveMode()
    WORKFLOW_SOURCE_FILE: base.ConstantBase = impl.WorkflowSourceFile()
    WORKFLOW_LOADER_CLASS: base.ConstantBase = impl.WorkflowLoaderClass()
    INTERNAL_DISPLAY_CLASS: base.ConstantBase = impl.InternalDisplayClass()
    EXTERNAL_DISPLAY_CLASS: base.ConstantBase = impl.ExternalDisplayClass()
    STRATEGY_CLASS: base.ConstantBase = impl.StrategyClass()
    USE_COLOR: base.ConstantBase = impl.UseColor()
    DEFAULT_SHELL_EXECUTABLE: base.ConstantBase = impl.DefaultShellExecutable()
    SHELL_INJECT_YIELD_FUNCTION: base.ConstantBase = impl.ShellInjectYieldFunction()
    STRICT_OUTCOMES_RENDERING: base.ConstantBase = impl.StrictOutcomesRendering()
    ACTION_CLASSES_DIRECTORIES: base.ConstantBase = impl.ActionClassDirectories()
    EXTERNAL_PYTHON_MODULES_PATHS: base.ConstantBase = impl.ExternalPythonModulesPaths()

    @classmethod
    def runtime_info(cls) -> list[base.ConstantValueInfo]:
        """Return set of info for all constants"""
        result: list[base.ConstantValueInfo] = []
        for attr_name, attr_type in sorted(get_class_annotations(cls).items()):
            if not isinstance(attr_type, type) or not issubclass(attr_type, base.ConstantBase):
                continue
            attr_value: t.Any = getattr(C, attr_name)
            attr_effective_source = base.CONSTANT_GLOBAL_SOURCES[attr_name]
            result.append(base.ConstantValueInfo(attr_name, attr_value, attr_effective_source))
        return result
