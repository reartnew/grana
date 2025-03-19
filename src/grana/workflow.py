"""Workflow-related module"""

from __future__ import annotations

import collections
import pathlib
import typing as t

from .actions.base import WorkflowActionExecution, ActionDependency
from .exceptions import IntegrityError
from .logging import WithLogger
from .rendering import WorkflowTemplar
from .config.constants.workflow import WorkflowConfiguration

__all__ = [
    "Workflow",
]


class Workflow(dict[str, WorkflowActionExecution], WithLogger):
    """Action relations map"""

    def __init__(
        self,
        actions_map: dict[str, WorkflowActionExecution],
        context: t.Optional[dict[str, t.Any]] = None,
        source_file: t.Optional[pathlib.Path] = None,
        configuration: t.Optional[WorkflowConfiguration] = None,
    ) -> None:
        super().__init__(actions_map)
        self.source_file: t.Optional[pathlib.Path] = source_file
        self.configuration: WorkflowConfiguration = configuration or WorkflowConfiguration()
        self._entrypoints: set[str] = set()
        self._tiers_sequence: list[list[WorkflowActionExecution]] = []
        self._descendants_map: dict[str, dict[str, ActionDependency]] = collections.defaultdict(dict)
        self.context: dict[str, t.Any] = context or {}
        # Check dependencies integrity
        self._establish_descendants()
        # Create order map to check all actions are reachable
        self._allocate_tiers()

    def get_templar(self, locals_map: dict) -> WorkflowTemplar:
        """Create a Templar object"""
        return WorkflowTemplar(
            outcomes_map={name: self[name].outcomes for name in self},
            action_states={name: self[name].status.value for name in self},
            context_map=self.context,
            metadata=self.get_metadata(),
            locals_map=locals_map,
        )

    def get_metadata(self) -> dict[str, t.Any]:
        """Obtain workflow metadata for further use in templating"""
        from .config.constants import C

        metadata: dict[str, t.Any] = {
            "cwd": C.CONTEXT_DIRECTORY,
        }
        if self.source_file is not None:
            source_file: pathlib.Path = self.source_file.resolve()
            metadata.update(
                {
                    "source_file": source_file,
                    "here": source_file.parent,
                }
            )
        return metadata

    def _establish_descendants(self) -> None:
        missing_deps: set[str] = set()
        for action_execution in self.values():  # type: WorkflowActionExecution
            for dependency in action_execution.ancestors:
                if dependency.name not in self:
                    missing_deps.add(dependency.name)
                    continue
                # Register symmetric descendant connection for further simplicity
                self._descendants_map[dependency.name][action_execution.name] = dependency
            # Check if there are any dependencies after removal at all
            if not action_execution.ancestors:
                self._entrypoints.add(action_execution.name)
        if missing_deps:
            raise IntegrityError(f"Missing actions among dependencies: {sorted(missing_deps)}")
        # Check entrypoints presence
        if not self._entrypoints:
            raise IntegrityError("No entrypoints for the workflow")

    def _allocate_tiers(self) -> None:
        """Use Dijkstra algorithm to introduce partial order.
        The tier is a group of tasks, and it's called finished when all its tasks are processed.
        Tier #0 consists of entrypoints.
        Tier #N consists of all tasks requiring exactly N-1 preceding tiers to be finished.
        """
        step_tier: int = 0
        action_execution_name_to_tier_mapping: dict[str, int] = {}
        #
        current_tier_actions_executions_names: set[str] = self._entrypoints
        while True:
            next_tier_candidate_actions_executions_names: set[str] = set()
            for tier_action_execution_name in current_tier_actions_executions_names:
                tier_action_execution: WorkflowActionExecution = self[tier_action_execution_name]
                if tier_action_execution.name in action_execution_name_to_tier_mapping:
                    continue
                action_execution_name_to_tier_mapping[tier_action_execution.name] = step_tier
                next_tier_candidate_actions_executions_names |= set(self._descendants_map[tier_action_execution_name])
            if not next_tier_candidate_actions_executions_names:
                break
            step_tier += 1
            current_tier_actions_executions_names = next_tier_candidate_actions_executions_names
        self.logger.debug(f"Number of tiers: {step_tier + 1}")
        unreachable_action_executions_names: set[str] = {
            execution.name for execution in self.values() if execution.name not in action_execution_name_to_tier_mapping
        }
        if unreachable_action_executions_names:
            raise IntegrityError(f"Unreachable actions found: {sorted(unreachable_action_executions_names)}")
        self._tiers_sequence = [[] for _ in range(step_tier + 1)]
        for action_execution_name, action_execution in self.items():
            action_execution_tier: int = action_execution_name_to_tier_mapping[action_execution_name]
            self._tiers_sequence[action_execution_tier].append(action_execution)

    def _iter_action_executions_by_tier(self) -> t.Generator[t.Tuple[int, WorkflowActionExecution], None, None]:
        """Yield actions tier by tier"""
        for tier_num, tier_executions in enumerate(self._tiers_sequence):
            for execution in tier_executions:
                yield tier_num, execution

    def iterate_actions(self) -> t.Iterator[WorkflowActionExecution]:
        """Iterate action executions sorted natively"""
        return (execution for _, execution in self._iter_action_executions_by_tier())
