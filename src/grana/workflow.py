"""Workflow-related module"""

from __future__ import annotations

import collections
import typing as t

from classlogging import LoggerMixin

from .actions.base import ActionBase, ActionDependency
from .exceptions import IntegrityError

__all__ = [
    "Workflow",
]


class Workflow(t.Dict[str, ActionBase], LoggerMixin):
    """Action relations map"""

    def __init__(
        self,
        actions_map: t.Dict[str, ActionBase],
        context: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> None:
        super().__init__(actions_map)
        self._entrypoints: t.Set[str] = set()
        self._tiers_sequence: t.List[t.List[ActionBase]] = []
        self._descendants_map: t.Dict[str, t.Dict[str, ActionDependency]] = collections.defaultdict(dict)
        self.context: t.Dict[str, t.Any] = context or {}
        # Check dependencies integrity
        self._establish_descendants()
        # Create order map to check all actions are reachable
        self._allocate_tiers()

    def _establish_descendants(self) -> None:
        missing_non_external_deps: t.Set[str] = set()
        for action in self.values():  # type: ActionBase
            for dependency_action_name, dependency in list(action.ancestors.items()):
                if dependency_action_name not in self:
                    if dependency.external:
                        # Get rid of missing external deps
                        action.ancestors.pop(dependency_action_name)
                    else:
                        missing_non_external_deps.add(dependency_action_name)
                    continue
                # Register symmetric descendant connection for further simplicity
                self._descendants_map[dependency_action_name][action.name] = dependency
            # Check if there are any dependencies after removal at all
            if not action.ancestors:
                self._entrypoints.add(action.name)
        if missing_non_external_deps:
            raise IntegrityError(f"Missing actions among dependencies: {sorted(missing_non_external_deps)}")
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
        action_name_to_tier_mapping: t.Dict[str, int] = {}
        #
        current_tier_actions_names: t.Set[str] = self._entrypoints
        while True:
            next_tier_candidate_actions_names: t.Set[str] = set()
            for tier_action_name in current_tier_actions_names:
                tier_action: ActionBase = self[tier_action_name]
                if tier_action.name in action_name_to_tier_mapping:
                    continue
                action_name_to_tier_mapping[tier_action.name] = step_tier
                next_tier_candidate_actions_names |= set(self._descendants_map[tier_action_name])
            if not next_tier_candidate_actions_names:
                break
            step_tier += 1
            current_tier_actions_names = next_tier_candidate_actions_names
        self.logger.debug(f"Number of tiers: {step_tier + 1}")
        unreachable_action_names: t.Set[str] = {
            action.name for action in self.values() if action.name not in action_name_to_tier_mapping
        }
        if unreachable_action_names:
            raise IntegrityError(f"Unreachable actions found: {sorted(unreachable_action_names)}")
        self._tiers_sequence = [[] for _ in range(step_tier + 1)]
        for action_name, action in self.items():
            action_tier: int = action_name_to_tier_mapping[action_name]
            self._tiers_sequence[action_tier].append(action)

    def iter_actions_by_tier(self) -> t.Generator[t.Tuple[int, ActionBase], None, None]:
        """Yield actions tier by tier"""
        for tier_num, tier_actions in enumerate(self._tiers_sequence):
            for action in tier_actions:
                yield tier_num, action
