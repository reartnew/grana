# pylint: disable=missing-class-docstring
"""Check constants engine"""

import os
import pathlib

import pytest
from pytest import MonkeyPatch

from grana.config.constants import C


def test_constant_with_boolean_env(monkeypatch: MonkeyPatch) -> None:
    """Check boolean env values"""

    C.reset_context_cache()
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "Y")
    assert C.SHELL_INJECT_YIELD_FUNCTION
    C.reset_context_cache()
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "N")
    assert not C.SHELL_INJECT_YIELD_FUNCTION
    C.reset_context_cache()
    monkeypatch.setenv("GRANA_SHELL_INJECT_YIELD_FUNCTION", "foo")
    with pytest.raises(ValueError):
        assert C.SHELL_INJECT_YIELD_FUNCTION


@pytest.mark.disable_constants_cache
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


def test_valid_log_level(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check valid log level"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".granarc").write_text("log_level: WARNING")
    assert C.LOG_LEVEL == "WARNING"


def test_invalid_log_level(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check invalid log level"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".granarc").write_text("log_level: FOO")
    with pytest.raises(ValueError, match="'FOO' is not a valid log level"):
        assert C.LOG_LEVEL
