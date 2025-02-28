"""Runner output processor default"""

import typing as t

from . import dialog
from .base import BaseDisplay
from .color import Color
from .utils import Tree, locate_parent_name_by_prefix
from ..actions.types import (
    Stderr,
    NamedMessageSource,
    RenamedMessageSource,
    ActionStatus,
)
from ..exceptions import InteractionError
from ..workflow import Workflow

__all__ = [
    "PrologueDisplay",
    "HeaderDisplay",
    "PrefixDisplay",
    "KNOWN_DISPLAYS",
]

ColorWrapperType = t.Callable[[str], str]


class PrologueDisplay(BaseDisplay):
    """Default display base"""

    NAME: str
    STATUS_TO_MARK_SYMBOL_MAP: dict[ActionStatus, str] = {
        ActionStatus.SKIPPED: "◯",
        ActionStatus.PENDING: "◯",
        ActionStatus.FAILURE: "✗",
        ActionStatus.WARNING: "✓",
        ActionStatus.RUNNING: "◯",
        ActionStatus.SUCCESS: "✓",
        ActionStatus.OMITTED: "◯",
    }
    STATUS_TO_COLOR_WRAPPER_MAP: dict[ActionStatus, ColorWrapperType] = {
        ActionStatus.SKIPPED: Color.gray,
        ActionStatus.PENDING: Color.gray,
        ActionStatus.FAILURE: Color.red,
        ActionStatus.WARNING: Color.yellow,
        ActionStatus.RUNNING: lambda x: x,
        ActionStatus.SUCCESS: Color.green,
        ActionStatus.OMITTED: Color.gray,
    }

    def __init__(self) -> None:
        super().__init__()
        self._status_topology: Tree[NamedMessageSource] = Tree()
        self._last_displayed_name: t.Optional[str] = None

    def _make_prologue(self, source: NamedMessageSource, mark: str) -> str:
        raise NotImplementedError

    def on_runner_start(self, children: t.Iterable[NamedMessageSource]) -> None:
        if not self._status_topology:
            self._status_topology.put((action.name, action) for action in children)
            return
        children_list: list[NamedMessageSource] = list(children)
        corresponding_action_name = locate_parent_name_by_prefix(
            children=(action.name for action in children_list),
            candidates=self._status_topology,
        )
        longest_match_length = len(corresponding_action_name)
        self._status_topology.put(
            (
                (action.name, RenamedMessageSource(origin=action, name=action.name[longest_match_length + 1 :]))
                for action in children_list
            ),
            parent_name=corresponding_action_name,
        )

    def on_action_message(self, source: NamedMessageSource, message: str) -> None:
        is_stderr: bool = isinstance(message, Stderr)
        for line in message.splitlines() if message else [message]:
            line_prefix: str = self._make_prologue(source=source, mark="*" if is_stderr else " ")
            self.display(f"{line_prefix}{Color.yellow(line) if is_stderr else line}")

    def on_action_error(self, source: NamedMessageSource, message: str) -> None:
        line_prefix: str = self._make_prologue(source=source, mark="!")
        for line in message.splitlines():
            super().on_action_error(
                source=source,
                message=f"{line_prefix}{Color.red(line)}",
            )

    def _generate_status_banner_lines(self) -> t.Generator[str, None, None]:
        for ascii_tree_prefix, source in self._status_topology.generate_ascii_representation():
            color: ColorWrapperType = self.STATUS_TO_COLOR_WRAPPER_MAP[source.status]
            status_mark: str = self.STATUS_TO_MARK_SYMBOL_MAP[source.status]
            status_part: str = f"{status_mark} {source.status.value}"
            yield f"{color(status_part)}: {Color.gray(ascii_tree_prefix)}{color(source.name)}"

    def on_runner_finish(self) -> None:
        """Show a text banner with the status info"""
        for line in self._generate_status_banner_lines():
            self.display(line)

    def on_plan_interaction(self, workflow: Workflow) -> None:
        displayed_action_names_with_descriptions: list[t.Tuple[str, str]] = []
        default_selected_action_names: list[str] = []
        for action in workflow.iterate_actions():
            if action.selectable:
                action_name_with_description: str = action.name
                if action.description is not None:
                    action_name_with_description = f"{action_name_with_description}: {action.description}"
                displayed_action_names_with_descriptions.append((action_name_with_description, action.name))
                default_selected_action_names.append(action.name)
        if not displayed_action_names_with_descriptions:
            raise InteractionError("No selectable actions found")
        selected_action_names: list[str] = dialog.run_dialog(
            choices=displayed_action_names_with_descriptions,
            default=default_selected_action_names,
        )
        self.logger.warning(f"Interactively selected actions: {selected_action_names}")
        for action in workflow.iterate_actions():
            if action.name in default_selected_action_names and action.name not in selected_action_names:
                self.logger.info(f"Disabling action: {action.name}")
                action.enabled = False


class PrefixDisplay(PrologueDisplay):
    """Adds prefixes to output chunks"""

    NAME = "prefixes"

    def __init__(self) -> None:
        super().__init__()
        self._action_names_max_len: int = 0

    def on_runner_start(self, children: t.Iterable[NamedMessageSource]) -> None:
        super().on_runner_start(children)
        self._action_names_max_len = max(self._action_names_max_len, *map(len, self._status_topology))

    def _make_prologue(self, source: NamedMessageSource, mark: str) -> str:
        """Construct prefix based on previous emitter action name"""
        justification_len: int = self._action_names_max_len + 2  # "2" here stands for square brackets
        formatted_name: str = (
            f"[{source.name}]".ljust(justification_len)
            if self._last_displayed_name != source.name
            else " " * justification_len
        )
        self._last_displayed_name = source.name
        return Color.gray(f"{formatted_name} {mark}| ")


class HeaderDisplay(PrologueDisplay):
    """Adds headers to output chunks"""

    NAME = "headers"

    def _close_block_if_necessary(self) -> None:
        if self._last_displayed_name is not None:
            self.display(Color.gray(" ╵"))

    def _make_prologue(self, source: NamedMessageSource, mark: str) -> str:
        """Construct header based on previous emitter action name"""
        if self._last_displayed_name != source.name:
            self._close_block_if_necessary()
            self.display(Color.gray(f" ┌─[{source.name}]"))
            self._last_displayed_name = source.name
        return Color.gray(f"{mark}│ ")

    def _generate_status_banner_lines(self) -> t.Generator[str, None, None]:
        """Add extra space in the beginning of the message, so it is aligned with the stream"""
        for line in super()._generate_status_banner_lines():
            yield f" {line}"

    def on_runner_finish(self) -> None:
        self._close_block_if_necessary()
        super().on_runner_finish()


KNOWN_DISPLAYS: dict[str, type[BaseDisplay]] = {
    HeaderDisplay.NAME: HeaderDisplay,
    PrefixDisplay.NAME: PrefixDisplay,
}
