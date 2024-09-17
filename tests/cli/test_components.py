"""Test miscellaneous CLI components"""

# pylint: disable=unused-argument

import pytest

from grana.config.constants import C
from grana.config.environment import Env
from grana.strategy import LooseStrategy, FreeStrategy
from grana.display.default import DefaultDisplay


def test_invalid_strategy_cli_arg(invalid_strategy_cli_arg: None) -> None:
    """Check error throw for bad CLI strategy arg value"""
    with pytest.raises(ValueError, match="Unrecognized value for the 'strategy' argument"):
        assert C.STRATEGY_CLASS


def test_default_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default strategy is loose"""
    monkeypatch.setattr(Env, "GRANA_STRATEGY_NAME", "")
    assert C.STRATEGY_CLASS is LooseStrategy


def test_valid_strategy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check resolution for good environment strategy variable value"""
    monkeypatch.setattr(Env, "GRANA_STRATEGY_NAME", "free")
    assert C.STRATEGY_CLASS is FreeStrategy


def test_invalid_strategy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check error throw for bad environment strategy variable value"""
    monkeypatch.setattr(Env, "GRANA_STRATEGY_NAME", "unknown-strategy")
    with pytest.raises(ValueError, match="Invalid strategy name:"):
        assert C.STRATEGY_CLASS


def test_default_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that default display is the DefaultDisplay"""
    monkeypatch.setattr(Env, "GRANA_DISPLAY_SOURCE_FILE", "")
    assert C.DISPLAY_CLASS is DefaultDisplay
