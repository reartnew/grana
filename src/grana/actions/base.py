"""Everything related to a default action interpretation"""

from __future__ import annotations

import asyncio
import base64
import enum
import re
import textwrap
import typing as t
from dataclasses import dataclass, fields

import classlogging

from .constants import ACTION_RESERVED_FIELD_NAMES
from .types import Stderr, EventType, OutcomeStorageType
from ..exceptions import ActionRunError

__all__ = [
    "ActionDependency",
    "ActionSeverity",
    "ActionBase",
    "ActionStatus",
    "ActionSkip",
    "ArgsBase",
    "EmissionScannerActionBase",
]


class ActionSkip(BaseException):
    """Stop executing action"""


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


class ActionSeverity(enum.Enum):
    """Action severity"""

    LOW = "low"
    NORMAL = "normal"


@dataclass
class ActionDependency:
    """Dependency info holder"""

    strict: bool = False
    external: bool = False


class ArgsMeta(type):
    """Metaclass for args containers that makes them all dataclasses"""

    def __new__(cls, name, bases, dct):
        sub_dataclass = dataclass(super().__new__(cls, name, bases, dct))
        reserved_names_collisions: t.Set[str] = {f.name for f in fields(sub_dataclass)} & ACTION_RESERVED_FIELD_NAMES
        if reserved_names_collisions:
            raise TypeError(f"Reserved names found in {name!r} class definition: {sorted(reserved_names_collisions)}")
        return sub_dataclass


@dataclass
class ArgsBase(metaclass=ArgsMeta):
    """Default empty args holder.
    Should be subclassed and then added to the `args` annotation of any action class."""


class ActionBase(classlogging.LoggerMixin):
    """Base class for all actions"""

    args: ArgsBase

    def __init__(
        self,
        name: str,
        args: ArgsBase = ArgsBase(),
        ancestors: t.Optional[t.Dict[str, ActionDependency]] = None,
        description: t.Optional[str] = None,
        selectable: bool = True,
        severity: ActionSeverity = ActionSeverity.NORMAL,
    ) -> None:
        self.name: str = name
        self.args: ArgsBase = args
        self.description: t.Optional[str] = description
        self.ancestors: t.Dict[str, ActionDependency] = ancestors or {}
        self.selectable: bool = selectable

        self._yielded_keys: OutcomeStorageType = {}
        self._status: ActionStatus = ActionStatus.PENDING
        self._enabled: bool = True
        # Do not create asyncio-related objects on constructing object to decouple from the event loop
        self._maybe_finish_flag: t.Optional[asyncio.Future] = None
        self._maybe_event_queue: t.Optional[asyncio.Queue[EventType]] = None
        self._running_task: t.Optional[asyncio.Task] = None
        self._severity: ActionSeverity = severity

    @property
    def enabled(self) -> bool:
        """Check whether the action has not been disabled"""
        return self._enabled

    def disable(self) -> None:
        """Marking the action as not planned for launch"""
        self.logger.info(f"Disabling {self}")
        if self._status != ActionStatus.PENDING:
            raise RuntimeError(f"Action {self.name} can't be disabled due to its status: {self._status!r}")
        self._enabled = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, status={self._status.value})"

    def yield_outcome(self, key: str, value: t.Any) -> None:
        """Report outcome key"""
        self.logger.debug(f"Yielded a key: {key!r}")
        self._yielded_keys[key] = value

    def get_outcomes(self) -> OutcomeStorageType:
        """Report all registered outcomes"""
        return self._yielded_keys

    def get_future(self) -> asyncio.Future:
        """Return a Future object indicating the end of the action"""
        if self._maybe_finish_flag is None:
            self._maybe_finish_flag = asyncio.get_event_loop().create_future()
        return self._maybe_finish_flag

    @property
    def _event_queue(self) -> asyncio.Queue[EventType]:
        if self._maybe_event_queue is None:
            self._maybe_event_queue = asyncio.Queue()
        return self._maybe_event_queue

    @property
    def status(self) -> ActionStatus:
        """Public getter"""
        return self._status

    async def run(self) -> None:
        """Main entry to be implemented in subclasses"""
        raise NotImplementedError

    async def _run_with_log_context(self) -> None:
        self.logger.info(f"Running action: {self.name!r}")
        with self.logger.context(name=self.name):
            return await self.run()

    async def _await(self) -> None:
        fut = self.get_future()
        if fut.done():
            return fut.result()
        # Allocate asyncio task
        if self._running_task is None:
            self._running_task = asyncio.create_task(self._run_with_log_context())
            self._status = ActionStatus.RUNNING
        try:
            if (running_task_result := await self._running_task) is not None:
                self.logger.warning(f"Action {self.name!r} return type is {type(running_task_result)} (not NoneType)")
        except ActionSkip:
            pass
        except ActionRunError:
            raise
        except Exception as e:
            self._internal_fail(e)
            raise
        else:
            self._status = ActionStatus.SUCCESS
        if not fut.done():
            fut.set_result(None)

    def emit(self, message: EventType) -> None:
        """Issue a message"""
        self._event_queue.put_nowait(message)

    def skip(self) -> t.NoReturn:
        """Set status to SKIPPED and stop execution"""
        self._internal_skip()
        raise ActionSkip

    def _internal_skip(self) -> None:
        self._status = ActionStatus.SKIPPED
        self.get_future().set_result(None)
        self.logger.info(f"Action {self.name!r} skipped")

    def _internal_omit(self) -> None:
        self._status = ActionStatus.OMITTED
        self.get_future().set_result(None)
        self.logger.info(f"Action {self.name!r} omitted")

    def fail(self, message: str) -> t.NoReturn:
        """Set corresponding error message and raise an exception"""
        exception = ActionRunError(message)
        self._internal_fail(exception)
        raise exception

    def _internal_fail(self, exception: Exception) -> None:
        if not self.get_future().done():
            self._status = ActionStatus.FAILURE if self._severity == ActionSeverity.NORMAL else ActionStatus.WARNING
            self.logger.info(f"Action {self.name!r} failed: {repr(exception)}")
            self.get_future().set_exception(exception)

    async def read_events(self) -> t.AsyncGenerator[EventType, None]:
        """Obtain all emitted events sequentially"""
        while True:
            # Wait for either an event or action finish
            queue_getter = asyncio.create_task(self._event_queue.get())
            await asyncio.wait(
                [self.get_future(), queue_getter],
                return_when=asyncio.FIRST_COMPLETED,
            )
            if queue_getter.done():
                yield queue_getter.result()
            if self.done():
                # The action is done, so we should drain the queue.
                # Prevent queue from async get since then.
                queue_getter.cancel()
                while True:
                    try:
                        yield self._event_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                return

    def __await__(self) -> t.Generator[t.Any, None, None]:
        return self._await().__await__()  # pylint: disable=no-member

    def done(self) -> bool:
        """Indicate whether the action is over"""
        return self.get_future().done() or self._status in (ActionStatus.SKIPPED, ActionStatus.OMITTED)


# pylint: disable=abstract-method
class EmissionScannerActionBase(ActionBase):
    """Base class for stream-scanning actions"""

    _SERVICE_MESSAGES_SCAN_PATTERN: t.ClassVar[t.Pattern] = re.compile(
        r"""^
          (.*?)  # possible preceding content
          \#\#grana\[  # message prefix
            ([A-Za-z0-9+/=\- ]+)  # message itself
          ]\#\#  # message suffix
        $""",
        re.VERBOSE,
    )
    _SHELL_SERVICE_FUNCTIONS_DEFINITIONS: str = textwrap.dedent(
        r"""
            yield_outcome(){
              [ "$1" = "" ] && echo "Missing key (first argument)" && return 1
              command -v base64 >/dev/null || ( echo "Missing command: base64" && return 2 )
              [ "$2" = "" ] && value="$(cat /dev/stdin)" || value="$2"
              echo "##grana[yield-outcome-b64 $(
                printf "$1" | base64 | tr -d '\n'
              ) $(
                printf "$value" | base64 | tr -d '\n'
              )]##"
              return 0
            }
            skip(){
              echo "##grana[skip]##"
              exit 0
            }
        """
    ).lstrip()

    def _process_service_message_expression(self, expression: str) -> None:
        try:
            expression_type, *encoded_args = expression.split()
            decoded_args: t.List[str] = [base64.b64decode(part, validate=True).decode() for part in encoded_args]
            if expression_type == "skip":
                self.skip()
            elif expression_type == "yield-outcome-b64":
                key, value = decoded_args
                self.logger.debug(f"Action {self.name!r} emission stream " f"reported an outcome: {key!r}")
                self.yield_outcome(key, value)
                return
            else:
                raise ValueError(f"Unrecognized expression: {expression!r}")
        except ActionSkip:  # pylint: disable=try-except-raise
            raise
        except Exception:
            self.logger.warning("Failed while parsing system message", exc_info=True)

    def emit(self, message: EventType) -> None:
        # Do not check stderr
        if isinstance(message, Stderr):
            super().emit(message)
            return
        memorized_prefix: str = ""
        for line in message.splitlines():
            # `endswith` is a cheaper check than re.findall
            if not line.endswith("]##") or not (matches := self._SERVICE_MESSAGES_SCAN_PATTERN.findall(line)):
                super().emit(memorized_prefix + line)
                memorized_prefix = ""
                continue
            for preceding_content, expression in matches:
                memorized_prefix += preceding_content
                self._process_service_message_expression(expression)
        # Do not forget to report system message prefix, if any
        if memorized_prefix:
            super().emit(memorized_prefix)
