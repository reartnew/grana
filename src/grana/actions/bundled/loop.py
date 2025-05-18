# pylint: disable=invalid-field-call
"""Separate module for loop action"""

import dataclasses
import itertools
import typing as t

from ..base import ArgsBase, ActionBase
from ...actions import constants
from ...display.types import DisplayEvent, DisplayEventName
from ...exceptions import ExecutionFailed
from ...rendering import CommonTemplar, containers as c

__all__ = [
    "LoopAction",
]

TOP_LEVEL_ONLY_ACTION_RESERVED_FIELD_NAMES: set[str] = constants.ACTION_RESERVED_FIELD_NAMES - {"type", "name"}


class LoopArgs(ArgsBase):
    """Loop step arguments."""

    matrix: dict[str, t.Any]
    step: dict[str, t.Any] = dataclasses.field(metadata={"rendering": "disabled"})
    strategy: t.Optional[str] = None
    strict: t.Optional[bool] = None


class LoopAction(ActionBase):
    """Executes an independent workflow and passes the display events to the original runner."""

    args: LoopArgs

    async def run(self) -> None:
        from ...config.constants import C
        from ...runner import Runner

        action: LoopAction = self

        def _resend_event_via_action(event: DisplayEvent) -> None:
            # These events shall not pass to the parent runner
            if event.name in (
                DisplayEventName.ON_RUNNER_FINISH,  # Triggers final status output
                DisplayEventName.ON_PLAN_INTERACTION,  # Pauses the execution
            ):
                event.future.set_result(None)  # Unlock the execution and continue
            else:
                self._communicator.send_display_event(event)  # Pass modified event

        class LoopRunner(Runner):
            """A runner that intercepts and filters out events"""

            async def _process_display_events(self) -> None:
                while True:
                    event: DisplayEvent = await self._events_flow.get()
                    _resend_event_via_action(event)

            async def run_async(self) -> None:
                try:
                    return await super().run_async()
                finally:
                    for sub_action in self.workflow.values():
                        action.yield_outcome(sub_action.name, c.OutcomeDict(sub_action.outcomes))

        # Cache [re]mount is required since the subflow may reconfigure some fields
        with C.mount_context_cache():
            # Check step vars
            if unexpected_fields := set(action.args.step) & TOP_LEVEL_ONLY_ACTION_RESERVED_FIELD_NAMES:
                raise ValueError(f"Unexpected `step` fields: {sorted(unexpected_fields)}")
            # Prepare ranges
            var_names: list[str] = []
            all_var_values: list[t.Any] = []
            for var_name, var_values in action.args.matrix.items():
                var_names.append(var_name)
                all_var_values.append(var_values)
            # Build actions
            actions: list[dict] = []
            for var_values_tuple in itertools.product(*all_var_values):
                matrix_locals_map: dict[str, t.Any] = c.AttrDict(zip(var_names, var_values_tuple))
                templar: CommonTemplar = self._communicator.get_templar(extra_locals=matrix_locals_map)
                action_dict: dict = templar.render(action.args.step)
                actions.append(action_dict)
            configuration: dict[str, t.Any] = {}
            if action.args.strategy is not None:
                configuration["strategy"] = action.args.strategy
            if action.args.strict is not None:
                configuration["strict"] = action.args.strict
            runner = LoopRunner({"actions": actions, "configuration": configuration})
            try:
                await runner.run_async()
            except ExecutionFailed:
                self.fail()
