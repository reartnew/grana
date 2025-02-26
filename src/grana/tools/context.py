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


class ContextCache:
    """Context-based cache for functions"""

    def __init__(self):
        self._cache: ContextManagerVar[dict] = ContextManagerVar()

    @contextlib.contextmanager
    def mount(self) -> t.Generator[None, None, None]:
        """Starts a new context for the cache"""
        with self._cache.set({}):
            yield

    def wrap(self, f: t.Callable) -> t.Callable:
        """A decorator to apply the cache to the function"""

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            try:
                local_context_cache_dict: dict = self._cache.get()
            except LookupError:
                # Cache is not mounted
                return f(*args, **kwargs)
            # Prepare the signature to store result
            key = functools._make_key((f,) + args, kwargs, False)  # pylint: disable=protected-access
            if key not in local_context_cache_dict:
                local_context_cache_dict[key] = f(*args, **kwargs)
            return local_context_cache_dict[key]

        return wrapped

    def clear(self) -> None:
        """Clears the cache for the active context"""
        self._cache.get().clear()
