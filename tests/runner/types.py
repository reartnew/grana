"""Types for runner tests."""

import typing as t
from pathlib import Path

__all__ = [
    "CtxFactoryType",
    "RunFactoryType",
]

CtxFactoryType = t.Callable[[str], Path]
RunFactoryType = t.Callable[[str], t.List[str]]
