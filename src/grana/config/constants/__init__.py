"""Lazy-loaded constants"""

import contextlib
import typing as t

from . import base, impl, rc, cache
from .cache import CACHE
from .cli import get_cli_option
from .helpers import class_from_module

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
    DEPENDENCY_DEFAULT_STRICTNESS: base.ConstantBase = impl.DependencyDefaultStrictness()
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
    SUBPROCESS_STREAM_BUFFER_LIMIT: base.ConstantBase = impl.SubprocessStreamBufferLimit()

    @classmethod
    def constants_info(cls) -> t.Iterable[base.ConstantProxyDescriptor]:
        """Return set of info for all constants"""
        for attr_name in sorted(dir(cls)):
            attr_value: t.Any = getattr(cls, attr_name)
            attr_value_origin: t.Any = getattr(attr_value, "__factory__", None)
            if isinstance(attr_value_origin, base.ConstantProxyDescriptor):
                yield attr_value_origin

    @classmethod
    def env_doc(cls) -> str:
        """Returns the info on the environment variables usage"""
        lines: list[str] = []
        for const_descriptor in cls.constants_info():
            lines.append(f"{const_descriptor.name}:")
            lines.extend(f"    {line.lstrip()}" for line in const_descriptor.definition.__doc__.splitlines())
        return "\n".join(lines)

    @classmethod
    @contextlib.contextmanager
    def mount_context_cache(cls) -> t.Generator[None, None, None]:
        """Enable context cache for all constants"""
        with CACHE.mount():
            yield

    @classmethod
    def reset_context_cache(cls) -> None:
        """Reset context cache for all constants"""
        CACHE.clear()
