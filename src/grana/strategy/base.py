"""
A strategy is an async-iterable object,
emitting actions one by one for further scheduling.
This module is for abstract base only.
"""

from __future__ import annotations

import typing as t

from ..actions.base import WorkflowActionExecution
from ..logging import WithLogger
from ..workflow import Workflow

ST = t.TypeVar("ST", bound="BaseStrategy")

__all__ = [
    "BaseStrategy",
]

_KNOWN_STRATEGIES: dict[str, type[BaseStrategy]] = {}


class BaseStrategy(WithLogger, t.AsyncIterable[WorkflowActionExecution]):
    """Strategy abstract base"""

    NAME: str = ""

    @staticmethod
    def get_strategy_class_by_name(name: str) -> type[BaseStrategy]:
        """Obtain derived strategy class by name"""
        try:
            return _KNOWN_STRATEGIES[name]
        except KeyError:
            raise ValueError(f"Invalid strategy name: {name!r} (allowed: {sorted(_KNOWN_STRATEGIES)})") from None

    def __init__(self, workflow: Workflow) -> None:
        self._workflow = workflow

    def __aiter__(self: ST) -> ST:
        return self

    async def __anext__(self) -> WorkflowActionExecution:
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        if _KNOWN_STRATEGIES.setdefault(cls.NAME, cls) is not cls:
            raise NameError(
                f"Strategy named {cls.NAME!r} already exists. "
                f"Please specify another name for the {cls.__module__}.{cls.__name__}."
            )
