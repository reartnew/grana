# pylint: disable=missing-class-docstring
"""Check constants engine"""

import os

import pytest
from pytest import MonkeyPatch

from grana.config.constants import C, Constant
from grana.config.constants.helpers import Mandatory


def test_mandatory_failure():
    """Validate mandatory variable ValueError"""

    class LocalConstants:
        FAILED = Mandatory(lambda: None)

    with pytest.raises(ValueError, match="getters failed"):
        assert LocalConstants.FAILED


def test_constant_with_boolean_env(monkeypatch: MonkeyPatch) -> None:
    """Check boolean env values"""

    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "Y")
    Constant.cache_clear()
    assert C.SHELL_INJECT_YIELD_FUNCTION is True
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "N")
    Constant.cache_clear()
    assert C.SHELL_INJECT_YIELD_FUNCTION is False
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "foo")
    Constant.cache_clear()
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
    Constant.cache_clear()
    assert C.USE_COLOR is True
    monkeypatch.setenv("GRANA_FORCE_COLOR", "N")
    Constant.cache_clear()
    assert C.USE_COLOR is False
    monkeypatch.setenv("GRANA_FORCE_COLOR", "")
    Constant.cache_clear()
    with pytest.raises(TTYException):
        assert C.USE_COLOR
    monkeypatch.setenv("GRANA_FORCE_COLOR", "foo")
    Constant.cache_clear()
    with pytest.raises(ValueError):
        assert C.USE_COLOR
