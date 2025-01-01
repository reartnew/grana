# pylint: disable=unused-argument,redefined-outer-name,missing-function-docstring
"""Display tests"""

import io
import typing as t

import pytest

from grana import exceptions, Runner
from grana.config.constants import C
from grana.config.environment import Env
from grana.display.base import BaseDisplay
from grana.display.default import PrologueDisplay, HeaderDisplay


class BadDisplay(BaseDisplay):
    """A display incapable of reporting runner start"""

    def on_runner_start(self, *args, **kwargs) -> None:
        raise RuntimeError


def test_bad_display() -> None:
    """Check that a bad display does not interrupt execution"""
    source = io.StringIO(
        """
        actions:
          - name: foo
            type: echo
            message: test
          - name: bar
            type: shell
            command: baz
        """
    )
    runner = Runner(source=source, display=BadDisplay())
    with pytest.raises(RuntimeError):
        runner.run_sync()


@pytest.mark.parametrize("display_name", ["headers", "prefixes"])
def test_prologue_displays_init(display_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check bundled displays"""
    monkeypatch.setattr(Env, "GRANA_DISPLAY_NAME", display_name)
    display_class = t.cast(PrologueDisplay, C.DISPLAY_CLASS)
    assert display_class.NAME == display_name


def test_invalid_display_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check display name validation"""
    monkeypatch.setattr(Env, "GRANA_DISPLAY_NAME", "unknown")
    with pytest.raises(ValueError, match="Display name should be one of"):
        assert C.DISPLAY_CLASS


def test_headers_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check headers display"""
    display_data: t.List[str] = []
    monkeypatch.setattr(HeaderDisplay, "display", display_data.append)
    monkeypatch.setattr(C, "DISPLAY_CLASS", HeaderDisplay)
    runner = Runner(
        source=io.StringIO(
            """---
actions:
  - name: Foo
    type: echo
    message: foo
  - name: Bar
    expects: Foo
    type: shell
    command: echo bar >&2 && exit 1
  - name: Baz
    expects:
      - name: Bar
        strict: True
    type: echo
    message: baz
"""
        )
    )
    with pytest.raises(exceptions.ExecutionFailed):
        runner.run_sync()
    assert display_data == [
        " ┌─[Foo]",
        " │ foo",
        " ╵",
        " ┌─[Bar]",
        "*│ bar",
        "!│ Exit code: 1",
        " ╵",
        " ✓ SUCCESS: Foo",
        " ✗ FAILURE: Bar",
        " ◯ SKIPPED: Baz",
    ]
