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

STREAM_DEFAULT_LOADER: type[AbstractBaseWorkflowLoader] = DefaultYAMLWorkflowLoader
DICT_DEFAULT_LOADER: type[AbstractBaseWorkflowLoader] = DefaultYAMLWorkflowLoader
SUFFIX_TO_LOADER_MAP: dict[str, type[AbstractBaseWorkflowLoader]] = {
    ".yml": DefaultYAMLWorkflowLoader,
    ".yaml": DefaultYAMLWorkflowLoader,
}


def get_default_loader_class_for_source(
    source: t.Union[Path, dict, io.TextIOBase],
) -> type[AbstractBaseWorkflowLoader]:
    """Return loader class based on file stats"""
    if isinstance(source, io.TextIOBase):
        return STREAM_DEFAULT_LOADER
    if isinstance(source, dict):
        return DICT_DEFAULT_LOADER
    if (loader_class := SUFFIX_TO_LOADER_MAP.get(source.suffix)) is None:
        raise SourceError(f"Unrecognized source: {source}")
    return loader_class
