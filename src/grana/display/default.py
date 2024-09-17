"""Runner output processor default"""

import sys
import typing as t

import inquirer  # type: ignore

from .base import BaseDisplay
from .color import Color
from ..actions.base import ActionBase, ActionStatus
from ..actions.types import Stderr
from ..exceptions import InteractionError
from ..workflow import Workflow

__all__ = [
    "PrologueDisplay",
    "HeaderDisplay",
    "PrefixDisplay",
    "DefaultDisplay",
    "KNOWN_DISPLAYS",
]


class PrologueDisplay(BaseDisplay):
    """Default display base"""

    NAME: str

    STATUS_TO_COLOR_WRAPPER_MAP: t.Dict[ActionStatus, t.Callable[[str], str]] = {
        ActionStatus.SKIPPED: Color.gray,
        ActionStatus.PENDING: Color.gray,
        ActionStatus.FAILURE: Color.red,
        ActionStatus.WARNING: Color.yellow,
        ActionStatus.RUNNING: lambda x: x,
        ActionStatus.SUCCESS: Color.green,
        ActionStatus.OMITTED: Color.gray,
    }

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._last_displayed_name: t.Optional[str] = None

    def _make_prologue(self, source: ActionBase, mark: str) -> str:
        raise NotImplementedError

    def emit_action_message(self, source: ActionBase, message: str) -> None:
        is_stderr: bool = isinstance(message, Stderr)
        for line in message.splitlines() if message else [message]:
            line_prefix: str = self._make_prologue(source=source, mark="*" if is_stderr else " ")
            self.display(f"{line_prefix}{Color.yellow(line) if is_stderr else line}")

    def emit_action_error(self, source: ActionBase, message: str) -> None:
        line_prefix: str = self._make_prologue(source=source, mark="!")
        for line in message.splitlines():
            super().emit_action_error(
                source=source,
                message=f"{line_prefix}{Color.red(line)}",
            )

    def _display_status_banner(self) -> None:
        """Show a text banner with the status info"""
        raise NotImplementedError

    def on_runner_finish(self) -> None:
        self._display_status_banner()

    def on_plan_interaction(self, workflow: Workflow) -> None:
        displayed_action_names: t.List[str] = []
        default_selected_action_names: t.List[str] = []
        for _, action in workflow.iter_actions_by_tier():
            if action.selectable:
                displayed_action_names.append(action.name)
                default_selected_action_names.append(action.name)
        selected_action_names: t.List[str] = self._run_dialog(
            displayed_action_names=displayed_action_names,
            default_selected_action_names=default_selected_action_names,
        )
        for action_name, action in workflow.items():
            if action_name in displayed_action_names and action_name not in selected_action_names:
                action.disable()

    @classmethod
    def _run_dialog(
        cls,
        displayed_action_names: t.List[str],
        default_selected_action_names: t.List[str],
    ) -> t.List[str]:  # pragma: no cover
        if not sys.stdin.isatty():
            raise InteractionError
        answers: t.Dict[str, t.List[str]] = inquirer.prompt(
            questions=[
                inquirer.Checkbox(
                    name="actions",
                    message="Select actions (SPACE to check, RETURN to proceed)",
                    choices=displayed_action_names,
                    default=default_selected_action_names,
                    carousel=True,
                )
            ],
            raise_keyboard_interrupt=True,
        )
        selected_action_names: t.List[str] = answers["actions"]
        return selected_action_names


class PrefixDisplay(PrologueDisplay):
    """Adds prefixes to output chunks"""

    NAME = "prefixes"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._action_names_max_len = max(map(len, self._workflow))

    def _make_prologue(self, source: ActionBase, mark: str) -> str:
        """Construct prefix based on previous emitter action name"""
        justification_len: int = self._action_names_max_len + 2  # "2" here stands for square brackets
        formatted_name: str = (
            f"[{source.name}]".ljust(justification_len)
            if self._last_displayed_name != source.name
            else " " * justification_len
        )
        self._last_displayed_name = source.name
        return Color.gray(f"{formatted_name} {mark}| ")

    def _display_status_banner(self) -> None:
        justification_len: int = self._action_names_max_len + 9  # "9" here stands for (e.g.) "SUCCESS: "
        self.display(Color.gray("=" * justification_len))
        for _, action in self._workflow.iter_actions_by_tier():
            color_wrapper: t.Callable[[str], str] = self.STATUS_TO_COLOR_WRAPPER_MAP[action.status]
            self.display(f"{color_wrapper(action.status.value)}: {action.name}")


class HeaderDisplay(PrologueDisplay):
    """Adds headers to output chunks"""

    NAME = "headers"
    _STATUS_TO_MARK_SYMBOL_MAP: t.Dict[ActionStatus, str] = {
        ActionStatus.SKIPPED: "◯",
        ActionStatus.PENDING: "◯",
        ActionStatus.FAILURE: "✗",
        ActionStatus.WARNING: "✓",
        ActionStatus.RUNNING: "◯",
        ActionStatus.SUCCESS: "✓",
        ActionStatus.OMITTED: "◯",
    }

    def _close_block_if_necessary(self) -> None:
        if self._last_displayed_name is not None:
            self.display(Color.gray(" ╵"))

    def _make_prologue(self, source: ActionBase, mark: str) -> str:
        """Construct header based on previous emitter action name"""
        if self._last_displayed_name != source.name:
            self._close_block_if_necessary()
            self.display(Color.gray(f" ┌─[{source.name}]"))
            self._last_displayed_name = source.name
        return Color.gray(f"{mark}│ ")

    def _display_status_banner(self) -> None:
        self._close_block_if_necessary()
        for _, action in self._workflow.iter_actions_by_tier():
            color_wrapper: t.Callable[[str], str] = self.STATUS_TO_COLOR_WRAPPER_MAP[action.status]
            mark_symbol: str = self._STATUS_TO_MARK_SYMBOL_MAP[action.status]
            state_string = f" {mark_symbol} {action.status.value}: {action.name}"
            self.display(color_wrapper(state_string))


DefaultDisplay = PrefixDisplay
KNOWN_DISPLAYS: t.Dict[str, t.Type[BaseDisplay]] = {
    HeaderDisplay.NAME: HeaderDisplay,
    PrefixDisplay.NAME: PrefixDisplay,
}
