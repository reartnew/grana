"""Lazy-loaded constants helpers"""

import functools
import hashlib
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

from ...exceptions import SourceError

__all__ = [
    "class_from_module",
]

VT = t.TypeVar("VT")
GetterType = t.Callable[[], t.Optional[VT]]

EXTERNALS_MODULES_PACKAGE: str = "grana.external"


@contextmanager
def add_sys_paths(*paths: Path) -> t.Iterator[None]:
    """Temporarily add paths to sys.path"""
    normalized_paths: list[str] = [str(path.absolute().expanduser()) for path in paths]
    for path in normalized_paths:
        sys.path.insert(0, path)
    try:
        yield
    finally:
        for path in normalized_paths:
            sys.path.remove(path)


@functools.cache
def load_external_module(source: Path, submodule_name: t.Optional[str] = None) -> ModuleType:
    """Load an external module"""
    from ..constants import C

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
    with add_sys_paths(*C.EXTERNAL_PYTHON_MODULES_PATHS):
        module_spec.loader.exec_module(module)  # type: ignore
    sys.modules[module_name] = module
    return module


def class_from_module(
    source_path: Path,
    class_name: str,
    submodule_name: t.Optional[str] = None,
) -> type:
    """Get a class from an external module, if given"""
    module: types.ModuleType = load_external_module(source_path, submodule_name)
    if not hasattr(module, class_name):
        raise AttributeError(f"External module contains no class {class_name!r} in {source_path!r}")
    return getattr(module, class_name)
