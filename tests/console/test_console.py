# pylint: disable=redefined-outer-name
"""CLI tests"""

import typing as t

import classlogging
import pytest
from click.testing import CliRunner
from dotenv.main import DotEnv

from grana import console, version
from grana.config.environment import Env

OptsType = t.Optional[t.List[str]]


class CLIError(Exception):
    """CLI test failure"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        text: str = f"<{code}>"
        if message:
            text += f" {message}"
        super().__init__(self, text)


class RunnerType(t.Protocol):
    """Protocol for the `run` fixture return type"""

    def __call__(
        self, text: t.Optional[str] = None, opts: OptsType = None, global_opts: OptsType = None
    ) -> t.List[str]: ...


BuilderType = t.Callable[[str], RunnerType]


def _invoke(*args, **kwargs) -> t.List[str]:
    result = CliRunner(mix_stderr=False).invoke(*args, **kwargs)
    if result.exit_code:
        raise CLIError(code=result.exit_code, message=result.stderr) from None
    return result.stdout.splitlines()


def _noop(*args, **kwargs) -> None:  # pylint: disable=unused-argument
    return None


@pytest.fixture
def builder(monkeypatch: pytest.MonkeyPatch) -> BuilderType:
    """Setup test command fed from stdin"""

    monkeypatch.setattr(DotEnv, "set_as_environment_variables", _noop)
    monkeypatch.setattr(classlogging, "configure_logging", _noop)

    def build(subcommand: str):
        def execute(text: t.Optional[str] = None, opts: OptsType = None, global_opts: OptsType = None) -> t.List[str]:
            return _invoke(console.main, (global_opts or []) + [subcommand, "-"] + (opts or []), input=text)

        return execute

    return build


@pytest.fixture
def run(builder: BuilderType) -> RunnerType:
    """Setup test run fed from stdin"""
    return builder("run")


@pytest.fixture
def validate(builder: BuilderType) -> RunnerType:
    """Setup test validate fed from stdin"""
    return builder("validate")


GOOD_WORKFLOW_TEXT: str = """---
actions:
  - type: echo
    message: foo
"""


def test_cli_version() -> None:
    """Check version command"""
    assert _invoke(console.main, ["info", "version"]) == [version.__version__]


def test_cli_validate(validate: RunnerType) -> None:
    """Check validate command"""
    assert validate(GOOD_WORKFLOW_TEXT) == []


def test_cli_env_vars() -> None:
    """Check env vars command"""
    doc: str = t.cast(str, Env.__doc__)
    assert _invoke(console.main, ["info", "env-vars"]) == doc.splitlines()


def test_cli_run(run: RunnerType) -> None:
    """Default run"""
    assert run(text=GOOD_WORKFLOW_TEXT) == [
        "[echo-0]  | foo",
        "===============",
        "SUCCESS: echo-0",
    ]


def test_cli_run_display(run: RunnerType) -> None:
    """Run with overridden display"""
    assert run(
        text=GOOD_WORKFLOW_TEXT,
        global_opts=["--display", "headers"],
    ) == [
        " ┌─[echo-0]",
        " │ foo",
        " ╵",
        " ✓ SUCCESS: echo-0",
    ]


@pytest.mark.parametrize("strategy", ["free", "sequential", "loose", "strict", "strict-sequential"])
def test_cli_run_explicit_strategy(run: RunnerType, strategy: str) -> None:
    """Run with overridden strategy"""
    assert run(
        text=GOOD_WORKFLOW_TEXT,
        opts=["--strategy", strategy],
    ) == [
        "[echo-0]  | foo",
        "===============",
        "SUCCESS: echo-0",
    ]


def test_cli_run_execution_failed(run: RunnerType) -> None:
    """Catch ExecutionFailed"""
    with pytest.raises(CLIError, match="<1>"):
        run(text="{actions: [{type: shell, command: foobar}]}")


def test_cli_run_load_error(run: RunnerType) -> None:
    """Catch LoadError"""
    with pytest.raises(CLIError, match="<102>"):
        run(text="actions:")


def test_cli_run_integrity_error(run: RunnerType) -> None:
    """Catch IntegrityError"""
    with pytest.raises(CLIError, match="<103>"):
        run(text="actions: []")


def test_cli_run_unhandled_exception(run: RunnerType) -> None:
    """Catch YAML parse error"""
    with pytest.raises(CLIError, match="<2>"):
        run(text="!@#$%^")


def test_cli_run_help(run: RunnerType) -> None:
    """CLI help"""
    assert "  Run pipeline immediately." in run(opts=["--help"])


def test_cli_multiple_positional_args(run: RunnerType) -> None:
    """Only one positional argument should be accepted"""
    with pytest.raises(CLIError, match="<2>"):
        run(opts=["foo", "bar"])
