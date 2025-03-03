"""Loader context"""

import contextlib
import typing as t
from pathlib import Path

from ..rendering import CommonTemplar
from ..tools.context import ContextManagerVar

__all__ = [
    "LOADED_FILE_STACK",
]


class LoadedFileStack:
    """Context variable that points to the loading file,
    which may be either a workflow file, runtime configuration file
    or a simple YAML file loaded by the `!load` tag."""

    def __init__(self):
        self._stack: ContextManagerVar[tuple[Path, ...]] = ContextManagerVar(default=tuple())

    @contextlib.contextmanager
    def add(self, path: Path) -> t.Generator[None, None, None]:
        """Add a path to the stack"""

        current_stack: tuple[Path, ...] = self._stack.get()
        with self._stack.set((path,) + current_stack):
            yield

    def get_all(self) -> tuple[Path, ...]:
        """Return all loading files in reversed order (from the active to the first)"""
        return self._stack.get()

    def get_last(self) -> t.Optional[Path]:
        """Return loading file, if any"""
        if not (stack := self.get_all()):
            return None
        return stack[0]

    def create_associated_templar(self) -> CommonTemplar:
        """Create proper common templar based on the current context."""
        current_loaded_file: t.Optional[Path] = self.get_last()
        if current_loaded_file is not None:
            return CommonTemplar.from_source_file(path=current_loaded_file)
        # This happens when the runner is fed from stdin
        return CommonTemplar.from_context_directory()


LOADED_FILE_STACK = LoadedFileStack()
