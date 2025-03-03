"""Available execution strategies"""

from __future__ import annotations

import asyncio
import typing as t

from .base import BaseStrategy
from ..actions.base import WorkflowActionExecution, ActionDependency
from ..exceptions import PendingActionUnresolvedOutcomeError, AutoStrategyCycleError
from ..workflow import Workflow

__all__ = [
    "ExplicitStrategy",
    "FreeStrategy",
    "SequentialStrategy",
    "AutoStrategy",
]


class ExplicitStrategy(BaseStrategy):
    """Actions are started immediately after their explicit dependencies have finished the execution.
    If no dependencies given for an action, then it is scheduled to start in the very beginning of the workflow run."""

    NAME = "explicit"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._pending: set[WorkflowActionExecution] = set(self._workflow.values())
        self._running: set[WorkflowActionExecution] = set()

    def _find_schedulable_execution(self) -> t.Optional[WorkflowActionExecution]:
        """Completely non-optimal (always scan all actions), but readable yet"""
        for execution in self._pending | self._running:
            if execution.future.done():
                self._running.discard(execution)
                continue
            if execution in self._pending and all(
                self._workflow[dependency.name].future.done() for dependency in execution.ancestors
            ):
                self.logger.debug(f"Action {execution.name!r} is ready for scheduling")
                return execution
        return None

    async def __anext__(self) -> WorkflowActionExecution:
        while True:
            # Get an execution and check whether to emit or to skip it
            execution: WorkflowActionExecution = await self._next_execution()
            self.logger.debug(f"The next action is: {execution}")
            self._pending.remove(execution)
            self._running.add(execution)
            return execution

    async def _next_execution(self) -> WorkflowActionExecution:
        while True:
            # Do we have anything pending already?
            if maybe_next_execution := self._find_schedulable_execution():
                return maybe_next_execution
            if not self._running:
                raise StopAsyncIteration
            await asyncio.wait(
                [execution.future for execution in self._running],
                return_when=asyncio.FIRST_COMPLETED,
            )


class FreeStrategy(ExplicitStrategy):
    """All actions are started immediately in parallel. All dependencies are ignored."""

    NAME = "free"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        for execution in self._workflow.values():
            if execution.ancestors:
                self.logger.warning(f"Ignoring action {execution.name!r} dependencies: {execution.ancestors}")
                execution.ancestors.clear()


class SequentialStrategy(FreeStrategy):
    """Actions run one-by-one in the same order they are specified in the workflow. All dependencies are ignored."""

    NAME = "sequential"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        executions: list[WorkflowActionExecution] = list(self._workflow.values())
        for num, execution in enumerate(executions):
            if num > 0:
                ancestor_name: str = executions[num - 1].name
                self.logger.debug(f"Adding an implicit dependency of {execution.name!r} on {ancestor_name!r}")
                execution.ancestors.append(ActionDependency(name=ancestor_name))


class AutoStrategy(ExplicitStrategy):
    """Use both explicit and outcome-based dependencies. Same as [](#explicit),
    but in case of referring to some action's outcome,
    an implicit dependency is added so the outcome could be resolved."""

    NAME = "auto"

    async def _next_execution(self) -> WorkflowActionExecution:
        try:
            while True:
                execution = await super()._next_execution()
                try:
                    execution.render_action_args()
                except PendingActionUnresolvedOutcomeError as e:
                    self.logger.info(f"Adding an automatic dependency of {execution.name!r} on {e.action_name!r}")
                    execution.ancestors.append(ActionDependency(name=e.action_name))
                    continue
                except Exception:  # nosec
                    # All other rendering exceptions are not important at this point
                    pass
                return execution
        except StopAsyncIteration:
            if self._pending:
                pending_actions: str = ", ".join(sorted(repr(execution.name) for execution in self._pending))
                error_text: str = (
                    f"The following actions went unreachable due to implicit dependencies: "
                    f"{pending_actions}. Check outcome references for circularity."
                )
                raise AutoStrategyCycleError(error_text) from None
            raise
