"""CLI components tests fixtures"""

import typing as t
from contextlib import contextmanager

import pytest

from grana.config.constants.cli import _CLI_OPTIONS


@pytest.fixture
def set_cli_opt() -> t.Callable[[str, str], t.ContextManager[None]]:
    """Temporarily set CLI option"""

    @contextmanager
    def set_opt(name: str, value: str) -> t.Generator[None, None, None]:
        sentinel = object()
        old_val = _CLI_OPTIONS.get(name, sentinel)
        _CLI_OPTIONS[name] = value
        yield
        del _CLI_OPTIONS[name]
        if old_val is not sentinel:
            _CLI_OPTIONS[name] = old_val

    return set_opt
