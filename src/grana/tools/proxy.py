"""Deferred proxy helpers."""

import dataclasses
import typing as t

__all__ = [
    "DeferredCallsProxy",
]


@dataclasses.dataclass
class DeferredCall:
    """Represents a call that will happen later"""

    method: t.Callable
    args: t.Tuple = tuple()
    kwargs: t.Dict[str, t.Any] = dataclasses.field(default_factory=dict)

    def __call__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


class DeferredCallsProxy:
    """Stores all calls to the proxy object methods to evaluate them after calling the `uncork` method"""

    def __init__(self, obj: t.Any) -> None:
        self.__obj: t.Any = obj
        self.__deferred_calls: t.Optional[t.List[DeferredCall]] = []

    def uncork(self) -> None:
        """Make all deferred calls happen in the sequential manner"""
        if self.__deferred_calls is None:
            return
        for deferred_call in self.__deferred_calls:
            deferred_call.method(*deferred_call.args, **deferred_call.kwargs)
        self.__deferred_calls = None

    def __getattr__(self, item: str) -> t.Any:
        proxy_attr: t.Any = getattr(self.__obj, item)
        if self.__deferred_calls is None or not callable(proxy_attr):
            return proxy_attr
        self.__deferred_calls.append(result := DeferredCall(method=proxy_attr))
        return result
