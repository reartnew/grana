"""Available execution strategies"""

from __future__ import annotations

import asyncio
import typing as t

from .base import BaseStrategy
from ..actions.base import WorkflowActionExecution
from ..actions.types import ActionStatus
from ..config.constants import C
from ..workflow import Workflow

__all__ = [
    "FreeStrategy",
    "SequentialStrategy",
    "ExplicitStrategy",
]


class FreeStrategy(BaseStrategy):
    """Free execution (fully parallel)"""

    NAME = "free"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._unprocessed: list[WorkflowActionExecution] = list(workflow.values())

    async def __anext__(self) -> WorkflowActionExecution:
        if not self._unprocessed:
            raise StopAsyncIteration
        return self._unprocessed.pop(0)


class SequentialStrategy(FreeStrategy):
    """Sequential execution"""

    NAME = "sequential"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._current: t.Optional[WorkflowActionExecution] = None

    async def __anext__(self) -> WorkflowActionExecution:
        if self._current is not None:
            try:
                await self._current.future
            except Exception:
                if C.DEPENDENCY_DEFAULT_STRICTNESS:
                    while True:
                        next_action = await super().__anext__()
                        self._skip_action(next_action)
        self._current = await super().__anext__()
        return self._current


class ExplicitStrategy(BaseStrategy):
    """Keep tracking dependencies states"""

    NAME = "explicit"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        # Actions that have been emitted by the strategy and not finished yet
        self._active_actions_map: dict[str, WorkflowActionExecution] = {}
        # Just a structured mutable copy of the dependency map
        self._action_blockers: dict[str, set[str]] = {name: set(workflow[name].ancestors) for name in workflow}

    def _skip_action(self, action: WorkflowActionExecution) -> None:
        super()._skip_action(action)
        self._active_actions_map.pop(action.name, None)

    def _get_maybe_next_action(self) -> t.Optional[WorkflowActionExecution]:
        """Completely non-optimal (always scan all actions), but readable yet"""
        done_action_names: set[str] = {action.name for action in self._workflow.values() if action.future.done()}
        # Copy into a list for further possible pop
        for maybe_next_action_name, maybe_next_action_blockers in list(self._action_blockers.items()):
            maybe_next_action_blockers -= done_action_names
            if not maybe_next_action_blockers:
                self.logger.debug(f"Action {maybe_next_action_name!r} is ready for scheduling")
                self._action_blockers.pop(maybe_next_action_name)
                next_action: WorkflowActionExecution = self._workflow[maybe_next_action_name]
                self._active_actions_map[next_action.name] = next_action
                return next_action
        return None

    async def __anext__(self) -> WorkflowActionExecution:
        while True:
            # Get an action and check whether to emit or to skip it
            next_action: WorkflowActionExecution = await self._next_action()
            self.logger.debug(f"The next action is: {next_action}")
            for ancestor_name, ancestor_dependency in next_action.ancestors.items():
                ancestor: WorkflowActionExecution = self._workflow[ancestor_name]
                if (
                    ancestor.status in (ActionStatus.FAILURE, ActionStatus.SKIPPED, ActionStatus.WARNING)
                    and ancestor_dependency.strict
                ):
                    self.logger.debug(f"Action {next_action} is qualified as skipped due to strict failure: {ancestor}")
                    self._skip_action(next_action)
                    break
            else:
                return next_action

    async def _next_action(self) -> WorkflowActionExecution:
        # Do we have anything pending already?
        if maybe_next_action := self._get_maybe_next_action():
            return maybe_next_action
        # Await for any actions finished. Can't directly apply asyncio.wait to Action objects
        # since python 3.11's implementation requires too many methods from an awaitable object.
        while active_actions := list(self._active_actions_map.values()):
            await asyncio.wait(
                [action.future for action in active_actions],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for action in active_actions:  # type: WorkflowActionExecution
                if action.future.done():
                    self.logger.debug(f"Action {action.name!r} execution finished")
                    del self._active_actions_map[action.name]
            # Maybe now?
            if maybe_next_action := self._get_maybe_next_action():
                return maybe_next_action
        raise StopAsyncIteration
