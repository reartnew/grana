"""Common loader utilities"""

import io
import typing as t
from pathlib import Path

from .base import AbstractBaseWorkflowLoader
from .default import DefaultYAMLWorkflowLoader
from ..exceptions import SourceError

__all__ = [
    "get_default_loader_class_for_source",
]

STREAM_DEFAULT_LOADER: t.Type[AbstractBaseWorkflowLoader] = DefaultYAMLWorkflowLoader
SUFFIX_TO_LOADER_MAP: t.Dict[str, t.Type[AbstractBaseWorkflowLoader]] = {
    ".yml": DefaultYAMLWorkflowLoader,
    ".yaml": DefaultYAMLWorkflowLoader,
}


def get_default_loader_class_for_source(
    source: t.Union[str, Path, io.TextIOBase],
) -> t.Type[AbstractBaseWorkflowLoader]:
    """Return loader class based on file stats"""
    if isinstance(source, io.TextIOBase):
        return STREAM_DEFAULT_LOADER
    source_path: Path = Path(source)
    if (loader_class := SUFFIX_TO_LOADER_MAP.get(source_path.suffix)) is None:
        raise SourceError(f"Unrecognized source: {source_path}")
    return loader_class
