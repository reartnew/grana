"""Separate module for subflow action"""

import functools
import typing as t
from collections.abc import Mapping, MutableMapping
from dataclasses import field
from pathlib import Path

from ..base import ArgsBase, ActionBase
from ..types import NamedMessageSource, ActionStatus
from ...display.types import DisplayEvent, DisplayEventName
from ...exceptions import ExecutionFailed
from ...rendering.containers import OutcomeDict

__all__ = [
    "SubflowAction",
]

ContextType = t.Dict[str, t.Any]


class SubflowArgs(ArgsBase):
    """Arguments applied to the subflow action."""

    path: Path
    context: ContextType = field(default_factory=dict)  # pylint: disable=invalid-field-call


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
        from ...runner import Runner  # pylint: disable=import-outside-toplevel,cyclic-import

        action: SubflowAction = self

        @functools.lru_cache()
        def _compose_source(origin: NamedMessageSource) -> CompositeSource:
            return CompositeSource(self, origin)

        def _resend_event_via_action(event: DisplayEvent) -> None:
            if event.name == DisplayEventName.ON_RUNNER_FINISH:
                # This event shall not pass to the parent runner since it triggers final status output.
                # Unlock the execution and continue.
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

            @classmethod
            def _deep_update_context(cls, receiver: ContextType, source: Mapping, path: str) -> ContextType:
                """Apply changes to the context"""
                for source_key, source_value in source.items():
                    sub_path: str = f"{path}.{source_key}" if path else source_key
                    if source_key not in receiver:
                        cls.logger.debug(f"Adding context: {sub_path}")
                        receiver[source_key] = source_value
                    elif isinstance(source_value, Mapping) and isinstance(receiver[source_key], MutableMapping):
                        cls.logger.trace(f"Merging context: {sub_path}")
                        receiver[source_key] = cls._deep_update_context(receiver[source_key], source_value, sub_path)
                    else:
                        cls.logger.debug(f"Rewriting context: {sub_path}")
                        receiver[source_key] = source_value
                return receiver

            async def run_async(self) -> None:
                self.workflow.context = self._deep_update_context(
                    receiver=self.workflow.context,
                    source=action.args.context,
                    path="",
                )
                try:
                    return await super().run_async()
                finally:
                    for sub_action_name, sub_action_outcomes in self._outcomes.items():
                        action.yield_outcome(sub_action_name, OutcomeDict(sub_action_outcomes))

        runner = SubflowRunner(source=self.args.path)
        try:
            await runner.run_async()
        except ExecutionFailed:
            self.fail()
