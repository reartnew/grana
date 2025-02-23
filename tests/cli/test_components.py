"""Test miscellaneous CLI components"""

# pylint: disable=unused-argument

import pytest

from grana.config.constants import C
from grana.display.default import DefaultDisplay
from grana.strategy.impl import ExplicitStrategy, FreeStrategy


def test_invalid_strategy_cli_arg(invalid_strategy_cli_opt) -> None:
    """Check error throw for bad CLI strategy option value"""
    with pytest.raises(ValueError, match="Invalid strategy name"):
        assert C.STRATEGY_CLASS


def test_default_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default strategy is `explicit`"""
    monkeypatch.delenv("GRANA_STRATEGY_NAME", raising=False)
    assert C.STRATEGY_CLASS == ExplicitStrategy


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
    """Check that default display is the DefaultDisplay"""
    monkeypatch.delenv("GRANA_DISPLAY_SOURCE_FILE", raising=False)
    assert C.INTERNAL_DISPLAY_CLASS == DefaultDisplay
