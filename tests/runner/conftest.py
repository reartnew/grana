"""Runner call fixtures"""

# pylint: disable=redefined-outer-name,unused-argument

import base64
import textwrap
import typing as t
from pathlib import Path

import aiodocker
import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest

import grana
from grana.config.environment import Env
from grana.display.default import DefaultDisplay
from .types import CtxFactoryType, RunFactoryType


@pytest.fixture(scope="session", autouse=True)
def disable_env_cache() -> None:
    """Do not cache environment variables values for varying tests"""
    Env.cache_values = False


@pytest.fixture
def display_collector(monkeypatch: pytest.MonkeyPatch) -> t.List[str]:
    """Creates display messages list instead of putting them to stdout"""
    results: t.List[str] = []

    # pylint: disable=unused-argument
    def display(self, message: str) -> None:
        results.append(message)

    # pylint: disable=unused-argument
    def _run_dialog(
        cls,
        displayed_action_names: t.List[str],
        default_selected_action_names: t.List[str],
    ) -> t.List[str]:
        return default_selected_action_names[:1]

    monkeypatch.setattr(DefaultDisplay, "display", display)
    monkeypatch.setattr(DefaultDisplay, "_run_dialog", _run_dialog)
    return results


@pytest.fixture
def ctx_from_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CtxFactoryType:
    """Context factory"""

    def make(data: str) -> Path:
        actions_source_path: Path = tmp_path / "grana.yaml"
        actions_source_path.write_bytes(textwrap.dedent(data).encode())
        monkeypatch.chdir(tmp_path)
        return actions_source_path

    return make


@pytest.fixture
def run_text(
    ctx_from_text: CtxFactoryType,
    display_collector: t.List[str],
    actions_definitions_directory: None,
) -> RunFactoryType:
    """Runner factory"""

    def run(data: str) -> t.List[str]:
        ctx_from_text(data)
        grana.Runner().run_sync()
        return display_collector

    return run


@pytest.fixture
def actions_definitions_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add actions definitions from directories"""
    actions_class_definitions_base_path: Path = Path(__file__).parent / "extension" / "modules" / "actions"
    monkeypatch.setenv(
        name="GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY",
        value=",".join(str(actions_class_definitions_base_path / sub_dir) for sub_dir in ("first", "second")),
    )


@pytest.fixture(params=["chdir", "env_workflow"])
def runner_good_context(ctx_from_text: CtxFactoryType, request: SubRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prepare a directory with good sample workflow files"""
    actions_source_path: Path = ctx_from_text(
        """
        actions:
          - name: Foo
            type: shell
            command: echo "foo"
          - name: Bar
            type: shell
            command: echo "bar" >&2
            expects:
              - Foo
        """
    )
    if request.param == "chdir":
        monkeypatch.chdir(actions_source_path.parent)
    elif request.param == "env_workflow":
        monkeypatch.setenv("GRANA_WORKFLOW_FILE", str(actions_source_path))
    else:
        raise ValueError(request.param)


@pytest.fixture(params=["chdir", "env_workflow"])
def runner_shell_yield_good_context(request: SubRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prepare a directory with good sample workflow files using shell yield feature"""

    def _str_to_b64(s: str) -> str:
        return base64.b64encode(s.encode()).decode()

    actions_source_path: Path = tmp_path / "grana.yaml"
    actions_source_path.write_bytes(
        f"""---
context:
    bar_prefix: Prefix
actions:
  - name: Foo
    type: shell
    command: yield_outcome result_key "I am foo" 
  - name: Qux
    type: shell
    command: printf "A\\nB\\nC\\n" | yield_outcome result_key 
  - name: Bar
    type: shell
    command: |
     echo "@{{outcomes.Foo.result_key}}"
     cat <<EOF
     @{{outcomes.Qux.result_key}}
     EOF
     echo "@{{context.bar_prefix}} ##grana[yield-outcome-b64 {_str_to_b64('result_key')} {_str_to_b64('bar')}]##"
    expects:
      - Foo
      - Qux
  - name: Baz
    type: shell
    command: echo "@{{outcomes.Bar.result_key}}"
    expects: Bar
  - name: Pivoslav
    type: shell
    command: skip
  - name: Egor
    type: shell
    command: yield_outcome A B C
    severity: low
""".encode()
    )
    if request.param == "chdir":
        monkeypatch.chdir(tmp_path)
    elif request.param == "env_workflow":
        monkeypatch.setenv("GRANA_WORKFLOW_FILE", str(actions_source_path))
    else:
        raise ValueError(request.param)


@pytest_asyncio.fixture
async def check_docker() -> None:
    """Skip if no docker context is available"""
    try:
        async with aiodocker.Docker():
            pass
    except Exception as e:
        pytest.skip(f"Unable to load docker context: {e!r}")
