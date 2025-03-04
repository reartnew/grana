# pylint: disable=invalid-field-call
"""Separate module for subflow action"""

import typing as t
from collections.abc import Mapping, MutableMapping
from dataclasses import field
from pathlib import Path

from ..base import ArgsBase, ActionBase
from ...display.types import DisplayEvent, DisplayEventName
from ...exceptions import ExecutionFailed
from ...rendering.containers import OutcomeDict

__all__ = [
    "SubflowAction",
]

ContextType = dict[str, t.Any]


class SubflowArgs(ArgsBase):
    """Arguments applied to the subflow action."""

    context: dict[str, t.Any] = field(default_factory=dict)
    path: t.Optional[Path] = None
    actions: t.Optional[list[dict[str, t.Any]]] = field(default=None)
    configuration: t.Optional[dict[str, t.Any]] = field(default=None)

    def __post_init__(self) -> None:
        is_path_based: bool = self.path is not None
        is_spec_based: bool = self.actions is not None or self.configuration is not None
        if is_path_based and is_spec_based:
            raise ValueError("Cannot specify both `path` and `actions`/`configuration`")
        if not is_path_based and not is_spec_based:
            raise ValueError("Either `path` or `actions` must be specified")


class SubflowAction(ActionBase):
    """Executes an independent workflow and passes the display events to the original runner."""

    args: SubflowArgs

    async def run(self) -> None:
        from ...config.constants import C
        from ...runner import Runner

        action: SubflowAction = self

        def _resend_event_via_action(event: DisplayEvent) -> None:
            # These events shall not pass to the parent runner
            if event.name in (
                DisplayEventName.ON_RUNNER_FINISH,  # Triggers final status output
                DisplayEventName.ON_PLAN_INTERACTION,  # Pauses the execution
            ):
                event.future.set_result(None)  # Unlock the execution and continue
            else:
                self._communicator.resend_display_event(event)  # Pass modified event

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
                        cls.logger.debug(f"Merging context: {sub_path}")
                        receiver[source_key] = cls._deep_update_context(receiver[source_key], source_value, sub_path)
                    else:
                        cls.logger.debug(f"Rewriting context: {sub_path}")
                        receiver[source_key] = source_value
                return receiver

            async def run_async(self) -> None:
                if action.args.path is not None:
                    self.workflow.context = self._deep_update_context(
                        receiver=self.workflow.context,
                        source=action.args.context,
                        path="",
                    )
                try:
                    return await super().run_async()
                finally:
                    for sub_action in self.workflow.values():
                        action.yield_outcome(sub_action.name, OutcomeDict(sub_action.outcomes))

        # Cache [re]mount is required since the subflow may reconfigure some fields
        with C.mount_context_cache():
            source: t.Union[Path, dict]
            if action.args.path is not None:
                source = action.args.path
            else:
                source = {
                    "actions": action.args.actions or [],
                    "context": action.args.context,
                    "configuration": action.args.configuration or {},
                }
            runner = SubflowRunner(source)
            try:
                await runner.run_async()
            except ExecutionFailed:
                self.fail()
