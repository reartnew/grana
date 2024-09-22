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


class BaseBadDisplay(BaseDisplay):
    """Bad displays base"""

    FAILURES: t.Set[str]
    METHOD_FAILURES_TO_CHECK: t.Set[str] = {
        "on_action_message",
        "on_action_error",
        "on_runner_start",
        "on_runner_finish",
        "on_action_start",
        "on_action_finish",
    }

    @classmethod
    def make_failure(cls, name: str) -> t.Callable:
        def failure(self, *args, **kwargs) -> t.Any:
            cls.FAILURES.add(name)
            raise RuntimeError

        return failure


@pytest.fixture
def bad_display() -> BaseBadDisplay:
    class BadDisplay(BaseBadDisplay):
        """A display incapable of doing anything"""

        FAILURES: t.Set[str] = set()

    for method_name in BaseBadDisplay.METHOD_FAILURES_TO_CHECK:
        setattr(BadDisplay, method_name, BadDisplay.make_failure(method_name))

    return BadDisplay(workflow=None)  # type: ignore[arg-type]


def test_bad_display(bad_display: BaseBadDisplay):
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
    runner = Runner(source=source, display=bad_display)
    with pytest.raises(exceptions.ExecutionFailed):
        runner.run_sync()
    assert bad_display.FAILURES == BaseBadDisplay.METHOD_FAILURES_TO_CHECK


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
