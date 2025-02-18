# pylint: disable=missing-class-docstring
"""Check constants engine"""

import os

import pytest
from pytest import MonkeyPatch

from grana.config.constants import C


def test_constant_with_boolean_env(monkeypatch: MonkeyPatch) -> None:
    """Check boolean env values"""

    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "Y")
    C.cache_clear()
    assert C.SHELL_INJECT_YIELD_FUNCTION
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "N")
    C.cache_clear()
    assert not C.SHELL_INJECT_YIELD_FUNCTION
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "foo")
    C.cache_clear()
    with pytest.raises(ValueError):
        assert C.SHELL_INJECT_YIELD_FUNCTION


def test_constant_with_ternary_env(monkeypatch: MonkeyPatch) -> None:
    """Check ternary env values"""

    class TTYException(Exception):
        pass

    def isatty(*args, **kwargs):
        raise TTYException

    monkeypatch.setenv("GRANA_FORCE_COLOR", "Y")
    C.cache_clear()
    assert C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "N")
    C.cache_clear()
    assert not C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "foo")
    C.cache_clear()
    with pytest.raises(ValueError):
        assert C.USE_COLOR
    monkeypatch.setattr(os, "isatty", isatty)
    monkeypatch.setenv("GRANA_FORCE_COLOR", "")
    C.cache_clear()
    with pytest.raises(TTYException):
        assert C.USE_COLOR
