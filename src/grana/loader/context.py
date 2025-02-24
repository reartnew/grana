"""Loader context"""

import typing as t
from pathlib import Path

from ..rendering import CommonTemplar
from ..tools.context import ContextManagerVar

__all__ = [
    "LOADED_FILE",
]


class LoadedFile(ContextManagerVar[Path]):
    """Context variable that points to the loading file,
    which may be either a workflow file, runtime configuration file
    or a simple YAML file loaded by the `!load` tag."""

    def __init__(self):
        super().__init__(default=None)

    def create_associated_templar(self) -> CommonTemplar:
        """Create proper common templar based on the current context."""
        current_loaded_file: t.Optional[Path] = self.get()
        if current_loaded_file is not None:
            return CommonTemplar.from_source_file(path=current_loaded_file)
        return CommonTemplar.from_context_directory()


LOADED_FILE = LoadedFile()
