"""Test miscellaneous CLI components"""

# pylint: disable=unused-argument

import pytest

from grana.config.constants import C
from grana.display.default import DefaultDisplay
from grana.strategy import ExplicitStrategy, FreeStrategy


def test_invalid_strategy_cli_arg(invalid_strategy_cli_arg: None) -> None:
    """Check error throw for bad CLI strategy arg value"""
    with pytest.raises(ValueError, match="Unrecognized value for the 'strategy' argument"):
        assert C.STRATEGY_CLASS


def test_default_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default strategy is `explicit`"""
    monkeypatch.setenv("GRANA_STRATEGY_NAME", "")
    assert C.STRATEGY_CLASS is ExplicitStrategy


def test_valid_strategy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check resolution for good environment strategy variable value"""
    monkeypatch.setenv("GRANA_STRATEGY_NAME", "free")
    assert C.STRATEGY_CLASS is FreeStrategy


def test_invalid_strategy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check error throw for bad environment strategy variable value"""
    monkeypatch.setenv("GRANA_STRATEGY_NAME", "unknown-strategy")
    with pytest.raises(ValueError, match="Invalid strategy name:"):
        assert C.STRATEGY_CLASS


def test_default_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default display is the DefaultDisplay"""
    monkeypatch.delenv("GRANA_DISPLAY_SOURCE_FILE", raising=False)
    assert C.DISPLAY_CLASS is DefaultDisplay
