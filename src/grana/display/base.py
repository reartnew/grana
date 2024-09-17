"""Runner output processor base"""

from ..actions.base import ActionBase
from ..exceptions import InteractionError
from ..workflow import Workflow

__all__ = [
    "BaseDisplay",
]


class BaseDisplay:
    """Base class for possible customizations"""

    def __init__(self, workflow: Workflow) -> None:
        self._workflow: Workflow = workflow

    def display(self, message: str) -> None:
        """Send text to the end user"""
        print(message.rstrip("\n"))

    # pylint: disable=unused-argument
    def emit_action_message(self, source: ActionBase, message: str) -> None:
        """Process a message from some source"""
        self.display(message)  # pragma: no cover

    # pylint: disable=unused-argument
    def emit_action_error(self, source: ActionBase, message: str) -> None:
        """Process an error from some source"""
        self.display(message)  # pragma: no cover

    def on_runner_start(self) -> None:
        """Runner start callback"""

    def on_runner_finish(self) -> None:
        """Runner finish callback"""

    def on_plan_interaction(self, workflow: Workflow) -> None:
        """Execution plan approval callback"""
        raise InteractionError  # pragma: no cover

    def on_action_start(self, action: ActionBase) -> None:
        """Action start callback"""

    def on_action_finish(self, action: ActionBase) -> None:
        """Action finish callback"""
