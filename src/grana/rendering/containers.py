"""Templar containers for rendering."""

import typing as t

import lazy_object_proxy  # type: ignore

from ..exceptions import ActionRenderError

__all__ = [
    "AttrDict",
    "LooseDict",
    "StrictOutcomeDict",
    "ActionContainingDict",
    "ContextDict",
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


class StrictOutcomeDict(AttrDict):
    """A dictionary that allows attribute read access to its keys with a default value fallback"""

    def __getitem__(self, item: str):
        try:
            return super().__getitem__(item)
        except KeyError as e:
            raise ActionRenderError(f"Outcome key {e} not found") from e


class ActionContainingDict(AttrDict):
    """Anything with action names as keys"""

    def __getitem__(self, item: str):
        try:
            return super().__getitem__(item)
        except KeyError as e:
            raise ActionRenderError(f"Action not found: {e}") from e


class ContextDict(AttrDict):
    """Context keys representation"""

    def __getitem__(self, item: str):
        # Context keys can refer to anything else, thus we keep resolving until the template is stable
        try:
            return super().__getitem__(item)
        except KeyError as e:
            raise ActionRenderError(f"Context key not found: {e}") from e


class LazyProxy(lazy_object_proxy.Proxy):
    """Lazy proxy that `repr`s like its wrapped object"""

    def __repr__(self, __getattr__=object.__getattribute__) -> str:
        return repr(self.__wrapped__)
