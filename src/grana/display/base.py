"""Runner output processor base"""

import typing as t

from ..actions.types import NamedMessageSource
from ..exceptions import InteractionError
from ..logging import WithLogger
from ..workflow import Workflow

__all__ = [
    "BaseDisplay",
]


class BaseDisplay(WithLogger):
    """Base class for possible customizations"""

    def display(self, message: str) -> None:
        """Send text to the end user"""
        print(message.rstrip("\n"))

    # pylint: disable=unused-argument
    def on_action_message(self, source: NamedMessageSource, message: str) -> None:
        """Process a message from some source"""
        self.display(message)  # pragma: no cover

    # pylint: disable=unused-argument
    def on_action_error(self, source: NamedMessageSource, message: str) -> None:
        """Process an error from some source"""
        self.display(message)  # pragma: no cover

    def on_runner_start(self, children: t.Iterable[NamedMessageSource]) -> None:
        """Runner start callback"""

    def on_runner_finish(self) -> None:
        """Runner finish callback"""

    def on_plan_interaction(self, workflow: Workflow) -> None:
        """Execution plan approval callback"""
        raise InteractionError  # pragma: no cover

    def on_action_start(self, source: NamedMessageSource) -> None:
        """Action start callback"""

    def on_action_finish(self, source: NamedMessageSource) -> None:
        """Action finish callback"""
