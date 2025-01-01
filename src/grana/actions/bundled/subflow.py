"""Separate module for subflow action"""

import functools
import typing as t
from pathlib import Path

from grana import ArgsBase, ActionBase, exceptions
from grana.actions.types import NamedMessageSource, ActionStatus
from grana.display.types import DisplayEvent, DisplayEventName

__all__ = [
    "SubflowAction",
]


class SubflowArgs(ArgsBase):
    """Arguments applied to the subflow action."""

    path: Path


class CompositeSource:
    """Event source built from multiple sources"""

    def __init__(self, *sources: NamedMessageSource) -> None:
        self._sources: t.Tuple[NamedMessageSource, ...] = sources

    @functools.cached_property
    def name(self) -> str:
        """Join component names"""
        return "/".join(source.name for source in self._sources)

    @property
    def status(self) -> ActionStatus:
        """Composite source status is the status of the first origin"""
        return self._sources[-1].status


class SubflowAction(ActionBase):
    """Executes an independent workflow and passes the display events to the original runner."""

    args: SubflowArgs

    async def run(self) -> None:
        from grana.runner import Runner  # pylint: disable=import-outside-toplevel

        @functools.lru_cache()
        def _compose_source(origin: NamedMessageSource) -> CompositeSource:
            return CompositeSource(self, origin)

        def _resend_event_via_action(event: DisplayEvent) -> None:
            if event.name == DisplayEventName.ON_RUNNER_FINISH:
                # Unlock the execution and continue
                event.future.set_result(None)
                return
            if event.name == DisplayEventName.ON_RUNNER_START:
                event.kwargs["children"] = map(_compose_source, event.kwargs["children"])
            elif origin := event.kwargs.get("source"):
                event.kwargs["source"] = _compose_source(origin)
            self._event_queue.put_nowait(event)

        class SubflowRunner(Runner):
            """A runner that intercepts and filters out events"""

            async def _process_display_events(self) -> None:
                while True:
                    event: DisplayEvent = await self._events_flow.get()
                    _resend_event_via_action(event)

        runner = SubflowRunner(source=self.args.path)
        try:
            await runner.run_async()
        except exceptions.ExecutionFailed:
            self.fail()
