# pylint: disable=invalid-field-call
"""Separate module for loop action"""

import dataclasses
import itertools
import typing as t

from .subflow import make_subflow_runner_class_for_action
from ..base import ArgsBase, ActionBase
from ...actions import constants
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
    actions: list[dict] = dataclasses.field(default_factory=list, init=False)


class LoopAction(ActionBase):
    """Executes an independent workflow and passes the display events to the original runner."""

    args: LoopArgs

    def on_render(self) -> None:
        if unexpected_fields := set(self.args.step) & TOP_LEVEL_ONLY_ACTION_RESERVED_FIELD_NAMES:
            raise ValueError(f"Unexpected `step` fields: {sorted(unexpected_fields)}")
        # Prepare ranges
        var_names: list[str] = []
        all_var_values: list[t.Any] = []
        for var_name, var_values in self.args.matrix.items():
            var_names.append(var_name)
            all_var_values.append(var_values)
        # Build actions
        actions: list[dict] = []
        for var_values_tuple in itertools.product(*all_var_values):
            matrix_locals_map: dict[str, t.Any] = c.AttrDict(zip(var_names, var_values_tuple))
            templar: CommonTemplar = self._communicator.get_templar(extra_locals=matrix_locals_map)
            action_dict: dict = templar.render(self.args.step)
            actions.append(action_dict)
        # Finally store built actions
        self.args.actions = actions

    async def run(self) -> None:
        from ...config.constants import C

        loop_runner_class = make_subflow_runner_class_for_action(self)

        # Cache [re]mount is required since the subflow may reconfigure some fields
        with C.mount_context_cache():
            # Prepare configuration section
            configuration: dict[str, t.Any] = {}
            if self.args.strategy is not None:
                configuration["strategy"] = self.args.strategy
            if self.args.strict is not None:
                configuration["strict"] = self.args.strict
            runner = loop_runner_class({"actions": self.args.actions, "configuration": configuration})
            try:
                await runner.run_async()
            except ExecutionFailed:
                self.fail()
