"""
A strategy is an async-iterable object,
emitting actions one by one for further scheduling.
"""

from __future__ import annotations

import asyncio
import typing as t

import classlogging

from .actions.base import ActionStatus, ActionBase, ActionSkip
from .workflow import Workflow

ST = t.TypeVar("ST", bound="BaseStrategy")

__all__ = [
    "BaseStrategy",
    "FreeStrategy",
    "SequentialStrategy",
    "LooseStrategy",
    "StrictStrategy",
    "StrictSequentialStrategy",
    "KNOWN_STRATEGIES",
]

KNOWN_STRATEGIES: t.Dict[str, t.Type[BaseStrategy]] = {}


class BaseStrategy(classlogging.LoggerMixin, t.AsyncIterable[ActionBase]):
    """Strategy abstract base"""

    NAME: str = ""
    STRICT: bool = False

    def __init__(self, workflow: Workflow) -> None:
        self._workflow = workflow

    def __aiter__(self: ST) -> ST:
        return self

    async def __anext__(self) -> ActionBase:
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        if KNOWN_STRATEGIES.setdefault(cls.NAME, cls) is not cls:
            raise NameError(
                f"Strategy named {cls.NAME!r} already exists. "
                f"Please specify another name for the {cls.__module__}.{cls.__name__}."
            )

    def _skip_action(self, action: ActionBase) -> None:
        try:
            action.skip()
        except ActionSkip:
            pass


class FreeStrategy(BaseStrategy):
    """Free execution (fully parallel)"""

    NAME = "free"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._unprocessed: t.List[ActionBase] = list(workflow.values())

    async def __anext__(self) -> ActionBase:
        if not self._unprocessed:
            raise StopAsyncIteration
        return self._unprocessed.pop(0)


class SequentialStrategy(FreeStrategy):
    """Sequential execution"""

    NAME = "sequential"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        self._current: t.Optional[ActionBase] = None

    async def __anext__(self) -> ActionBase:
        if self._current is not None:
            try:
                await self._current
            except Exception:
                if self.STRICT:
                    while True:
                        next_action = await super().__anext__()
                        self._skip_action(next_action)
        self._current = await super().__anext__()
        return self._current


class LooseStrategy(BaseStrategy):
    """Keep tracking dependencies states"""

    NAME = "loose"

    def __init__(self, workflow: Workflow) -> None:
        super().__init__(workflow)
        # Actions that have been emitted by the strategy and not finished yet
        self._active_actions_map: t.Dict[str, ActionBase] = {}
        # Just a structured mutable copy of the dependency map
        self._action_blockers: t.Dict[str, t.Set[str]] = {name: set(workflow[name].ancestors) for name in workflow}

    def _skip_action(self, action: ActionBase) -> None:
        super()._skip_action(action)
        self._active_actions_map.pop(action.name, None)

    def _get_maybe_next_action(self) -> t.Optional[ActionBase]:
        """Completely non-optimal (always scan all actions), but readable yet"""
        done_action_names: t.Set[str] = {action.name for action in self._workflow.values() if action.done()}
        # Copy into a list for further possible pop
        for maybe_next_action_name, maybe_next_action_blockers in list(self._action_blockers.items()):
            maybe_next_action_blockers -= done_action_names
            if not maybe_next_action_blockers:
                self.logger.debug(f"Action {maybe_next_action_name!r} is ready for scheduling")
                self._action_blockers.pop(maybe_next_action_name)
                next_action: ActionBase = self._workflow[maybe_next_action_name]
                self._active_actions_map[next_action.name] = next_action
                return next_action
        return None

    async def __anext__(self) -> ActionBase:
        while True:
            # Get an action and check whether to emit or to skip it
            next_action: ActionBase = await self._next_action()
            self.logger.debug(f"The next action is: {next_action}")
            for ancestor_name, ancestor_dependency in next_action.ancestors.items():
                ancestor: ActionBase = self._workflow[ancestor_name]
                if ancestor.status in (ActionStatus.FAILURE, ActionStatus.SKIPPED, ActionStatus.WARNING) and (
                    ancestor_dependency.strict or self.STRICT
                ):
                    self.logger.debug(f"Action {next_action} is qualified as skipped due to strict failure: {ancestor}")
                    self._skip_action(next_action)
                    break
            else:
                return next_action

    async def _next_action(self) -> ActionBase:
        # Do we have anything pending already?
        if maybe_next_action := self._get_maybe_next_action():
            return maybe_next_action
        # Await for any actions finished. Can't directly apply asyncio.wait to Action objects
        # since python 3.11's implementation requires too many methods from an awaitable object.
        while active_actions := list(self._active_actions_map.values()):
            await asyncio.wait(
                [action.get_future() for action in active_actions],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for action in active_actions:  # type: ActionBase
                if action.done():
                    self.logger.debug(f"Action {action.name!r} execution finished")
                    del self._active_actions_map[action.name]
            # Maybe now?
            if maybe_next_action := self._get_maybe_next_action():
                return maybe_next_action
        raise StopAsyncIteration


class StrictStrategy(LooseStrategy):
    """Respect all dependencies, but force them strict"""

    STRICT = True
    NAME = "strict"


class StrictSequentialStrategy(SequentialStrategy):
    """Linear execution until first failure"""

    STRICT = True
    NAME = "strict-sequential"
