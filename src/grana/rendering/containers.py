"""Templar containers for rendering."""

import importlib
import types
import typing as t

from .proxy import LazyProxy
from ..exceptions import ActionRenderError, PendingActionUnresolvedOutcomeError
from ..logging import WithLogger

__all__ = [
    "AttrDict",
    "LooseDict",
    "OutcomeDict",
    "ActionContainingDict",
    "ExternalModulesDict",
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


class ExternalModulesDict(AttrDict, WithLogger):
    """Container for accessing external modules inside templars"""

    def __init__(self):
        super().__init__()
        self._known_modules: t.Dict[str, types.ModuleType] = {}

    def __getitem__(self, key):
        if key not in self._known_modules:
            self._known_modules[key] = self._load_module(key)
        return self._known_modules[key]

    @classmethod
    def _load_module(cls, module_alias: str):
        from ..config.constants import C, helpers

        if (actual_module_name := C.TEMPLAR_MODULES_WHITELIST.get(module_alias)) is None:
            raise KeyError(f"Module alias {module_alias!r} is not added to the templar modules whitelist")
        cls.logger.debug(f"Module alias {module_alias!r} resolved to {actual_module_name!r}")
        with helpers.add_sys_paths(*C.EXTERNAL_PYTHON_MODULES_PATHS):
            return importlib.import_module(actual_module_name)
