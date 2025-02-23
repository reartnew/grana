# pylint: disable=missing-class-docstring
"""Check constants engine"""

import os

import pytest
from pytest import MonkeyPatch

from grana.config.constants import C


def test_constant_with_boolean_env(monkeypatch: MonkeyPatch) -> None:
    """Check boolean env values"""

    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "Y")
    assert C.SHELL_INJECT_YIELD_FUNCTION
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "N")
    assert not C.SHELL_INJECT_YIELD_FUNCTION
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "foo")
    with pytest.raises(ValueError):
        assert C.SHELL_INJECT_YIELD_FUNCTION


def test_constant_with_ternary_env(monkeypatch: MonkeyPatch) -> None:
    """Check ternary env values"""

    class TTYException(Exception):
        pass

    def isatty(*args, **kwargs):
        raise TTYException

    monkeypatch.setenv("GRANA_FORCE_COLOR", "Y")
    assert C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "N")
    assert not C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "foo")
    with pytest.raises(ValueError):
        assert C.USE_COLOR
    monkeypatch.setattr(os, "isatty", isatty)
    monkeypatch.setenv("GRANA_FORCE_COLOR", "")
    with pytest.raises(TTYException):
        assert C.USE_COLOR
