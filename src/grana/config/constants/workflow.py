"""Workflow-based configuration values"""

import contextlib
import dataclasses
import typing as t

from ...tools.context import ContextManagerVar

__all__ = [
    "WorkflowConfiguration",
    "CONTEXT_HOLDER",
]

CONTEXT_HOLDER: ContextManagerVar[dict[str, t.Any]] = ContextManagerVar(default={})


class ConfigSentinel:
    """Sentinel type for workflow configuration parameters"""


sentinel = ConfigSentinel()


@dataclasses.dataclass
class WorkflowConfiguration:
    """Configuration loaded from the workflow"""

    strategy: t.Union[str, ConfigSentinel] = sentinel

    @contextlib.contextmanager
    def apply(self) -> t.Generator[None, None, None]:
        """Apply contextual values for the workflow configuration"""
        cfg_dict: t.Dict[str, t.Any] = {
            k: v for k, v in dataclasses.asdict(self).items() if not isinstance(v, ConfigSentinel)
        }
        with CONTEXT_HOLDER.set(cfg_dict):
            yield
