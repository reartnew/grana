# pylint: disable=missing-class-docstring
"""Check constants engine"""

import os

import pytest
from pytest import MonkeyPatch

from grana.config.constants import C
from grana.config.constants.base import ConstantBase


def test_constant_with_boolean_env(monkeypatch: MonkeyPatch) -> None:
    """Check boolean env values"""

    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "Y")
    ConstantBase.cache_clear()
    assert C.SHELL_INJECT_YIELD_FUNCTION
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "N")
    ConstantBase.cache_clear()
    assert not C.SHELL_INJECT_YIELD_FUNCTION
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "foo")
    ConstantBase.cache_clear()
    with pytest.raises(ValueError):
        assert C.SHELL_INJECT_YIELD_FUNCTION


def test_constant_with_ternary_env(monkeypatch: MonkeyPatch) -> None:
    """Check ternary env values"""

    class TTYException(Exception):
        pass

    def isatty(*args, **kwargs):
        raise TTYException

    monkeypatch.setattr(os, "isatty", isatty)
    monkeypatch.setenv("GRANA_FORCE_COLOR", "Y")
    ConstantBase.cache_clear()
    assert C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "N")
    ConstantBase.cache_clear()
    assert not C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "")
    ConstantBase.cache_clear()
    with pytest.raises(TTYException):
        assert C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "foo")
    ConstantBase.cache_clear()
    with pytest.raises(ValueError):
        assert C.USE_COLOR
