"""Test miscellaneous CLI components"""

import pathlib

# pylint: disable=unused-argument

import pytest

from grana.config.constants import C
from grana.display.default import PrefixDisplay
from grana.strategy.impl import AutoStrategy, FreeStrategy


def test_invalid_strategy_cli_arg(set_cli_opt) -> None:
    """Check error throw for bad CLI strategy option value"""
    with set_cli_opt("strategy", "unknown-strategy"):
        with pytest.raises(ValueError, match="Invalid strategy name"):
            assert C.STRATEGY_CLASS


def test_default_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default strategy is `auto`"""
    monkeypatch.delenv("GRANA_STRATEGY_NAME", raising=False)
    assert C.STRATEGY_CLASS == AutoStrategy


def test_valid_strategy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check resolution for good environment strategy variable value"""
    monkeypatch.setenv("GRANA_STRATEGY_NAME", "free")
    assert C.STRATEGY_CLASS == FreeStrategy


def test_invalid_strategy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check error throw for bad environment strategy variable value"""
    monkeypatch.setenv("GRANA_STRATEGY_NAME", "unknown-strategy")
    with pytest.raises(ValueError, match="Invalid strategy name:"):
        assert C.STRATEGY_CLASS


def test_default_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default display is the PrefixDisplay"""
    monkeypatch.delenv("GRANA_DISPLAY_SOURCE_FILE", raising=False)
    assert C.INTERNAL_DISPLAY_CLASS == PrefixDisplay


def test_external_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that external display is loaded properly"""
    monkeypatch.setenv("GRANA_DISPLAY_SOURCE_FILE", str(pathlib.Path(__file__).parent / "external_display.py"))
    assert C.EXTERNAL_DISPLAY_CLASS.__wrapped__.__doc__ == "Test external display"
