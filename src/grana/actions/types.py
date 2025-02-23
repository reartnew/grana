"""Types collection"""

import abc
import dataclasses
import enum
import typing as t

__all__ = [
    "NamedMessageSource",
    "RenamedMessageSource",
    "Stderr",
    "Expression",
    "qualify_string_as_potentially_renderable",
    "ActionStatus",
]


class ActionStatus(enum.Enum):
    """Action valid states"""

    PENDING = "PENDING"  # Enabled, but not started yet
    RUNNING = "RUNNING"  # Execution in process
    SUCCESS = "SUCCESS"  # Finished without errors
    WARNING = "WARNING"  # Erroneous action with low severity
    FAILURE = "FAILURE"  # Erroneous action
    SKIPPED = "SKIPPED"  # May be set by action itself
    OMITTED = "OMITTED"  # Disabled during interaction

    def __repr__(self) -> str:
        return self.name

    __str__ = __repr__


class NamedMessageSource(t.Protocol, t.Hashable):
    """Anything that can be a message source (e.g. an action instance)"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Source name"""

    @property
    @abc.abstractmethod
    def status(self) -> ActionStatus:
        """Source status"""

    @property
    @abc.abstractmethod
    def description(self) -> t.Optional[str]:
        """Source info"""


class RenamedMessageSource:
    """Renamed message source"""

    def __init__(self, name: str, origin: NamedMessageSource) -> None:
        self.name: str = name
        self._origin: NamedMessageSource = origin

    @property
    def status(self) -> ActionStatus:
        """Proxy to the origin status"""
        return self._origin.status

    @property
    def description(self) -> t.Optional[str]:
        """Proxy to the origin description"""
        return self._origin.description  # pragma: no cover


class Stderr(str):
    """Strings related to standard error stream"""


@dataclasses.dataclass
class Expression:
    """Complex object expression to be rendered later"""

    expression: str


def qualify_string_as_potentially_renderable(data: str) -> bool:
    """Check that a string should be templated later"""
    return "@{" in data
