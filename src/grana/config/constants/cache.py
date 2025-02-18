"""Constants cache"""

from ...tools.context import ContextManagerVar

__all__ = [
    "CONSTANTS_CACHE",
    "RC_CACHE",
]

CONSTANTS_CACHE: ContextManagerVar[dict] = ContextManagerVar(default={})
RC_CACHE: ContextManagerVar[list] = ContextManagerVar(default=[])
