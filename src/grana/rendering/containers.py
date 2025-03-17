"""Templar containers for rendering."""

import typing as t

from .proxy import LazyProxy
from ..exceptions import ActionRenderError, PendingActionUnresolvedOutcomeError

__all__ = [
    "AttrDict",
    "LooseDict",
    "OutcomeDict",
    "ActionContainingDict",
    "LazyProxy",
]

RenderHookType = t.Callable[[str], str]


class ItemAttributeAccessorMixin:
    """Anything, that can be accessed fie __getitem__, is available also as an attribute"""

    def __getattr__(self, item: str):
        return self.__getitem__(item)


class AttrDict(dict, ItemAttributeAccessorMixin):
    """Basic dictionary that allows attribute read access to its keys"""


class LooseDict(AttrDict):
    """A dictionary that allows attribute read access to its keys with a default empty value fallback"""

    def __getitem__(self, item: str):
        try:
            return super().__getitem__(item)
        except KeyError:
            return ""


class OutcomeDict(AttrDict):
    """A dictionary that allows attribute read access to its keys with a default value fallback"""

    def __getitem__(self, item: str):
        try:
            return super().__getitem__(item)
        except KeyError as e:
            from ..config.constants import C

            if C.STRICT_OUTCOMES_RENDERING:
                raise ActionRenderError(f"Outcome key {e} not found") from e
            return ""


class ActionContainingDict(AttrDict):
    """Anything with action names as keys"""

    def __getitem__(self, item: str):
        try:
            return super().__getitem__(item)
        except KeyError as e:
            raise ActionRenderError(f"Action not found: {e}") from e


class ActionOutcomeAggregateDict(ActionContainingDict):
    """Top-level container for action outcomes"""

    def __getitem__(self, item: str):
        if (result := super().__getitem__(item)) is not None:
            return result
        raise PendingActionUnresolvedOutcomeError(item)
