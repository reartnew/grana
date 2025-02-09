"""Workflow-based configuration values"""

import contextlib
import contextvars
import dataclasses
import typing as t

__all__ = [
    "WorkflowConfiguration",
    "CONTEXT_HOLDER",
]

CONTEXT_HOLDER: contextvars.ContextVar[dict[str, t.Any]] = contextvars.ContextVar("CONTEXT_HOLDER", default={})


@dataclasses.dataclass
class WorkflowConfiguration:
    """Configuration loaded from the workflow"""

    strategy: t.Optional[str] = None

    @contextlib.contextmanager
    def propagate(self) -> t.Generator[None, None, None]:
        """Apply contextual values for the workflow configuration"""
        token: contextvars.Token = CONTEXT_HOLDER.set(dataclasses.asdict(self))
        try:
            yield
        finally:
            CONTEXT_HOLDER.reset(token)
