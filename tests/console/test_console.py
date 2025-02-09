# pylint: disable=redefined-outer-name
"""CLI tests"""

import typing as t

import pytest
from click.testing import CliRunner

from grana import console, version, logging
from grana.config.constants.environment import ENV_DOC

OptsType = t.Optional[list[str]]


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
    ) -> list[str]: ...


class BuilderType(t.Protocol):
    """Protocol for the `builder` fixture return type"""

    def __call__(self, *commands: str) -> RunnerType: ...


def _invoke(*args, **kwargs) -> list[str]:
    result = CliRunner(mix_stderr=False).invoke(*args, **kwargs)
    if result.exit_code:
        raise CLIError(code=result.exit_code, message=result.stderr) from None
    return result.stdout.rstrip().splitlines()


def _noop(*args, **kwargs) -> None:  # pylint: disable=unused-argument
    return None


@pytest.fixture
def builder(monkeypatch: pytest.MonkeyPatch) -> BuilderType:
    """Setup test command fed from stdin"""

    monkeypatch.setattr(logging, "configure_logging", _noop)

    def build(*subcommand: str):
        def execute(text: t.Optional[str] = None, opts: OptsType = None, global_opts: OptsType = None) -> list[str]:
            return _invoke(console.main, (global_opts or []) + list(subcommand) + (opts or []), input=text)

        return execute

    return build


@pytest.fixture
def run_cmd(builder: BuilderType) -> RunnerType:
    """Setup test run fed from stdin"""
    return builder("run", "-")


@pytest.fixture
def validate_cmd(builder: BuilderType) -> RunnerType:
    """Setup test validate fed from stdin"""
    return builder("validate", "-")


@pytest.fixture
def version_cmd(builder: BuilderType) -> RunnerType:
    """Setup test version"""
    return builder("version")


@pytest.fixture
def runtime_info_cmd(builder: BuilderType) -> RunnerType:
    """Setup test info runtime"""
    return builder("info", "runtime")


GOOD_WORKFLOW_TEXT: str = """---
actions:
  - type: echo
    message: foo
"""


def test_cli_version(version_cmd: RunnerType) -> None:
    """Check version command"""
    assert version_cmd() == [version.__version__]


def test_cli_validate(validate_cmd: RunnerType) -> None:
    """Check validate command"""
    assert validate_cmd(GOOD_WORKFLOW_TEXT) == []


def test_cli_env_vars() -> None:
    """Check env vars command"""
    assert _invoke(console.main, ["info", "env-vars"]) == ENV_DOC.rstrip().splitlines()


def test_cli_run(run_cmd: RunnerType) -> None:
    """Default run"""
    assert run_cmd(text=GOOD_WORKFLOW_TEXT) == [
        "[echo]  | foo",
        "✓ SUCCESS: echo",
    ]


def test_cli_run_display(run_cmd: RunnerType) -> None:
    """Run with overridden display"""
    assert run_cmd(
        text=GOOD_WORKFLOW_TEXT,
        global_opts=["--display", "headers"],
    ) == [
        " ┌─[echo]",
        " │ foo",
        " ╵",
        " ✓ SUCCESS: echo",
    ]


@pytest.mark.parametrize("strategy", ["free", "sequential", "explicit", "strict", "strict-sequential"])
def test_cli_run_explicit_strategy(run_cmd: RunnerType, strategy: str) -> None:
    """Run with overridden strategy"""
    assert run_cmd(
        text=GOOD_WORKFLOW_TEXT,
        opts=["--strategy", strategy],
    ) == [
        "[echo]  | foo",
        "✓ SUCCESS: echo",
    ]


def test_cli_run_execution_failed(run_cmd: RunnerType) -> None:
    """Catch ExecutionFailed"""
    with pytest.raises(CLIError, match="<1>"):
        run_cmd(text="{actions: [{type: shell, command: foobar}]}")


def test_cli_run_load_error(run_cmd: RunnerType) -> None:
    """Catch LoadError"""
    with pytest.raises(CLIError, match="<102>"):
        run_cmd(text="actions:")


def test_cli_run_integrity_error(run_cmd: RunnerType) -> None:
    """Catch IntegrityError"""
    with pytest.raises(CLIError, match="<103>"):
        run_cmd(text="actions: []")


def test_cli_run_unhandled_exception(run_cmd: RunnerType) -> None:
    """Catch YAML parse error"""
    with pytest.raises(CLIError, match="<2>"):
        run_cmd(text="!@#$%^")


def test_cli_run_help(run_cmd: RunnerType) -> None:
    """CLI help"""
    assert "  Run the pipeline." in run_cmd(opts=["--help"])


def test_cli_multiple_positional_args(run_cmd: RunnerType) -> None:
    """Only one positional argument should be accepted"""
    with pytest.raises(CLIError, match="<2>"):
        run_cmd(opts=["foo", "bar"])


@pytest.mark.parametrize("opts", [[], ["--show-defaults"]], ids=["without-defaults", "with-defaults"])
def test_info_runtime(runtime_info_cmd: RunnerType, opts: list[str]) -> None:
    """Check `grana info runtime` command"""
    info: list[str] = runtime_info_cmd(opts=opts)
    assert "Python" in info
    assert "Configuration" in info
    assert "Actions" in info
