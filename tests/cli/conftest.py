"""CLI components tests fixtures"""

import typing as t
from contextlib import contextmanager

import pytest

from grana.config.constants.cli import _CLI_OPTIONS


@contextmanager
def _cli_arg(name: str, value: str) -> t.Generator[None, None, None]:
    """Temporarily set CLI argument"""
    sentinel = object()
    old_val = _CLI_OPTIONS.get(name, sentinel)
    _CLI_OPTIONS[name] = value
    yield
    del _CLI_OPTIONS[name]
    if old_val is not sentinel:
        _CLI_OPTIONS[name] = old_val


@pytest.fixture
def invalid_strategy_cli_arg() -> t.Generator[None, None, None]:
    """Set invalid strategy CLI arg"""
    with _cli_arg(name="strategy", value="unknown-strategy"):
        yield
