"""Runner-related constants helpers"""

import typing as t
from pathlib import Path

from ...tools.context import ContextManagerVar

__all__ = [
    "TEMP_DIR_CONTEXT",
]

TEMP_DIR_CONTEXT: ContextManagerVar[t.Optional[Path]] = ContextManagerVar(default=None)
