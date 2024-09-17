"""Lazy-loaded constants helpers"""

import hashlib
import os
import sys
import types
import typing as t
from contextlib import contextmanager
from importlib.machinery import ModuleSpec
from importlib.util import (
    spec_from_file_location,
    module_from_spec,
)
from pathlib import Path
from types import ModuleType

from ..environment import Env
from ...exceptions import SourceError

__all__ = [
    "Optional",
    "Mandatory",
    "maybe_path",
    "maybe_class_from_module",
]

VT = t.TypeVar("VT")
GetterType = t.Callable[[], t.Optional[VT]]

EXTERNALS_MODULES_PACKAGE: str = "grana.external"


@contextmanager
def add_sys_paths(*paths: str) -> t.Iterator[None]:
    """Temporarily add paths to sys.path"""
    normalized_paths: t.List[str] = [os.path.expanduser(os.path.abspath(path)) for path in paths]
    for path in normalized_paths:
        sys.path.insert(0, path)
    try:
        yield
    finally:
        for path in normalized_paths:
            sys.path.remove(path)


def load_external_module(source: Path, submodule_name: t.Optional[str] = None) -> ModuleType:
    """Load an external module"""
    if not source.is_file():
        raise SourceError(f"Missing source module: {source}")
    if submodule_name is None:
        submodule_name = hashlib.md5(str(source).encode()).hexdigest()  # nosec  # pragma: no cover
    module_name: str = f"{EXTERNALS_MODULES_PACKAGE}.{submodule_name}"
    module_spec: t.Optional[ModuleSpec] = spec_from_file_location(
        name=module_name,
        location=source,
    )
    if module_spec is None:
        raise SourceError(f"Can't read module spec from source: {source}")
    module: ModuleType = module_from_spec(module_spec)
    with add_sys_paths(*Env.GRANA_EXTERNAL_MODULES_PATHS):
        module_spec.loader.exec_module(module)  # type: ignore
    sys.modules[module_name] = module
    return module


class Optional(t.Generic[VT]):
    """Optional lazy variable"""

    def __init__(self, *getters: GetterType) -> None:
        self._getters: t.Tuple[GetterType, ...] = getters
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: t.Any, owner: type) -> t.Optional[VT]:
        getter_result: t.Optional[VT] = None
        for getter in self._getters:
            if (getter_result := getter()) is not None:
                break
        return getter_result


class Mandatory(Optional, t.Generic[VT]):
    """Mandatory lazy variable"""

    def __get__(self, instance: t.Any, owner: type) -> VT:
        result: t.Optional[VT] = super().__get__(instance, owner)
        if result is None:
            raise ValueError(f"{self._name!r} getters failed")
        return result


def maybe_path(path_str: str) -> t.Optional[Path]:
    """Transform a string into an optional path"""
    return Path(path_str) if path_str else None


def maybe_class_from_module(path_str: str, class_name: str, submodule_name: t.Optional[str] = None) -> t.Optional[type]:
    """Get a class from an external module, if given"""
    if (source_path := maybe_path(path_str)) is None:
        return None
    module: types.ModuleType = load_external_module(source_path, submodule_name)
    if not hasattr(module, class_name):
        raise AttributeError(f"External module contains no class {class_name!r} in {path_str!r}")
    return getattr(module, class_name)
