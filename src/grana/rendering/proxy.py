"""Lazy proxy implementation"""

import operator
import os
import typing as t
import weakref
from functools import cached_property

__all__ = [
    "LazyProxy",
]


def _make_method(func: t.Callable) -> t.Callable:
    """Create proxy method"""

    def method_over_wrapped(self, *args, **kwargs):
        return func(self.__wrapped__, *args, **kwargs)

    return method_over_wrapped


def _make_r_method(func: t.Callable) -> t.Callable:
    """Create proxy method with positional args in reversed order"""

    def method_over_wrapped(self, other):
        return func(other, self.__wrapped__)

    return method_over_wrapped


# pylint: disable=inconsistent-return-statements
class LazyProxy:
    """Perform evaluation only once when it is required first time"""

    def __init__(self, factory):
        self.__dict__["__factory__"] = factory

    @cached_property
    def __wrapped__(self):
        return self.__dict__["__factory__"]()

    def __setattr__(self, __name, __value) -> None:
        if __name not in ("__wrapped__", "__factory__"):
            return setattr(self.__wrapped__, __name, __value)
        self.__dict__[__name] = __value

    def __getattr__(self, __name) -> t.Any:
        if __name not in ("__wrapped__", "__factory__"):
            return getattr(self.__wrapped__, __name)
        return self.__dict__[__name]

    def __delattr__(self, __name):
        if __name not in ("__wrapped__", "__factory__"):
            return delattr(self.__wrapped__, __name)
        del self.__dict__[__name]

    # operator.call is available only since python 3.11
    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)

    __name__ = property(_make_method(operator.attrgetter("__name__")))  # type: ignore[assignment]
    __module__ = property(_make_method(operator.attrgetter("__module__")))  # type: ignore[assignment]
    __doc__ = property(_make_method(operator.attrgetter("__doc__")))  # type: ignore[assignment]
    __annotations__ = property(_make_method(operator.attrgetter("__annotations__")))  # type: ignore[assignment]
    __class__ = property(_make_method(operator.attrgetter("__class__")))  # type: ignore[assignment]
    __weakref__ = property(_make_method(weakref.ref))
    __enter__ = _make_method(operator.attrgetter("__enter__"))
    __exit__ = _make_method(operator.attrgetter("__exit__"))
    __dir__ = _make_method(dir)
    __str__ = _make_method(str)
    __bytes__ = _make_method(bytes)
    __repr__ = _make_method(repr)
    __reversed__ = _make_method(reversed)
    __round__ = _make_method(round)
    __lt__ = _make_method(operator.lt)
    __le__ = _make_method(operator.le)
    __eq__ = _make_method(operator.eq)
    __ne__ = _make_method(operator.ne)
    __gt__ = _make_method(operator.gt)
    __ge__ = _make_method(operator.ge)
    __hash__ = _make_method(hash)
    __bool__ = _make_method(bool)
    __add__ = _make_method(operator.add)
    __sub__ = _make_method(operator.sub)
    __mul__ = _make_method(operator.mul)
    __matmul__ = _make_method(operator.matmul)
    __truediv__ = _make_method(operator.truediv)
    __floordiv__ = _make_method(operator.floordiv)
    __mod__ = _make_method(operator.mod)
    __divmod__ = _make_method(divmod)
    __pow__ = _make_method(pow)
    __lshift__ = _make_method(operator.lshift)
    __rshift__ = _make_method(operator.rshift)
    __and__ = _make_method(operator.and_)
    __xor__ = _make_method(operator.xor)
    __or__ = _make_method(operator.or_)
    __radd__ = _make_r_method(operator.add)
    __rsub__ = _make_r_method(operator.sub)
    __rmul__ = _make_r_method(operator.mul)
    __rmatmul__ = _make_r_method(operator.matmul)
    __rtruediv__ = _make_r_method(operator.truediv)
    __rfloordiv__ = _make_r_method(operator.floordiv)
    __rmod__ = _make_r_method(operator.mod)
    __rdivmod__ = _make_r_method(divmod)
    __rpow__ = _make_r_method(pow)
    __rlshift__ = _make_r_method(operator.lshift)
    __rrshift__ = _make_r_method(operator.rshift)
    __rand__ = _make_r_method(operator.and_)
    __rxor__ = _make_r_method(operator.xor)
    __ror__ = _make_r_method(operator.or_)
    __iadd__ = _make_method(operator.iadd)
    __isub__ = _make_method(operator.isub)
    __imul__ = _make_method(operator.imul)
    __imatmul__ = _make_method(operator.imatmul)
    __itruediv__ = _make_method(operator.itruediv)
    __ifloordiv__ = _make_method(operator.ifloordiv)
    __imod__ = _make_method(operator.imod)
    __ipow__ = _make_method(operator.ipow)
    __ilshift__ = _make_method(operator.ilshift)
    __irshift__ = _make_method(operator.irshift)
    __iand__ = _make_method(operator.iand)
    __ixor__ = _make_method(operator.ixor)
    __ior__ = _make_method(operator.ior)
    __neg__ = _make_method(operator.neg)
    __pos__ = _make_method(operator.pos)
    __abs__ = _make_method(operator.abs)
    __invert__ = _make_method(operator.invert)
    __int__ = _make_method(int)
    __float__ = _make_method(float)
    __oct__ = _make_method(oct)
    __hex__ = _make_method(hex)
    __index__ = _make_method(operator.index)
    __len__ = _make_method(len)
    __contains__ = _make_method(operator.contains)
    __getitem__ = _make_method(operator.getitem)
    __setitem__ = _make_method(operator.setitem)
    __delitem__ = _make_method(operator.delitem)
    __iter__ = _make_method(iter)
    __fspath__ = _make_method(os.fspath)
