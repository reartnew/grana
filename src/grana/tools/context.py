"""Context variables base"""

import contextlib
import contextvars
import functools
import typing as t
import uuid

__all__ = [
    "ContextManagerVar",
    "ContextCache",
]

VT = t.TypeVar("VT")


class ContextManagerVar(t.Generic[VT]):
    """ContextVar with context manager"""

    def __init__(self, **kwargs):
        self._ctx_var: contextvars.ContextVar[VT] = contextvars.ContextVar(uuid.uuid4().hex, **kwargs)

    @contextlib.contextmanager
    def set(self, value):
        """Set context value"""
        token = self._ctx_var.set(value)
        try:
            yield
        finally:
            self._ctx_var.reset(token)

    def get(self) -> VT:
        """Get context value"""
        return self._ctx_var.get()


PT = t.ParamSpec("PT")
RT = t.TypeVar("RT")


class ContextCache:
    """Context-based cache for functions"""

    def __init__(self):
        self._cache: t.Optional[ContextManagerVar[dict]] = None

    @contextlib.contextmanager
    def mount(self) -> t.Generator[None, None, None]:
        """Starts a new context for the cache"""
        self._cache = ContextManagerVar()
        try:
            with self._cache.set({}):
                yield
        finally:
            self._cache = None

    def wrap(self, f: t.Callable[PT, RT]) -> t.Callable[PT, RT]:
        """A decorator to apply the cache to the function"""

        @functools.wraps(f)
        def wrapped(*args: PT.args, **kwargs: PT.kwargs) -> RT:
            key = functools._make_key(args, kwargs, False)  # pylint: disable=protected-access
            if self._cache is None:
                return f(*args, **kwargs)
            try:
                local_context_cache: dict = self._cache.get()
            except LookupError:
                return f(*args, **kwargs)
            if key not in local_context_cache:
                local_context_cache[key] = f(*args, **kwargs)
            return local_context_cache[key]

        return wrapped
