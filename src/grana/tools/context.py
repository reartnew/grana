"""Context variables base"""

import contextlib
import contextvars
import uuid
import typing as t

__all__ = [
    "ContextManagerVar",
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
