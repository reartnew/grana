"""Everything related to a default action interpretation"""

from __future__ import annotations

import asyncio
import base64
import collections
import enum
import re
import textwrap
import typing as t
from dataclasses import dataclass, fields

import classlogging

from .constants import ACTION_RESERVED_FIELD_NAMES
from .types import Stderr, OutcomeStorageType, ActionStatus
from ..display.types import DisplayEvent, DisplayEventName
from ..exceptions import ActionRunError

__all__ = [
    "ActionDependency",
    "ActionSeverity",
    "ActionBase",
    "ActionSkip",
    "ArgsBase",
    "EmissionScannerActionBase",
]


class ActionSkip(BaseException):
    """Stop executing action"""


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
        self._maybe_message_queue: t.Optional[asyncio.Queue[DisplayEvent]] = None
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
    def _event_queue(self) -> asyncio.Queue[DisplayEvent]:
        if self._maybe_message_queue is None:
            self._maybe_message_queue = asyncio.Queue()
        return self._maybe_message_queue

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

    def say(self, message: str) -> None:
        """Send a message to the display"""
        self._event_queue.put_nowait(DisplayEvent(DisplayEventName.ON_ACTION_MESSAGE, source=self, message=message))

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

    def fail(self, message: str = "") -> t.NoReturn:
        """Set corresponding error message and raise an exception"""
        exception = ActionRunError(message)
        self._internal_fail(exception)
        raise exception

    def _internal_fail(self, exception: Exception) -> None:
        if not self.get_future().done():
            self._status = ActionStatus.FAILURE if self._severity == ActionSeverity.NORMAL else ActionStatus.WARNING
            self.logger.info(f"Action {self.name!r} failed: {repr(exception)}")
            self.get_future().set_exception(exception)

    async def read_messages(self) -> t.AsyncGenerator[DisplayEvent, None]:
        """Obtain all said messages sequentially"""
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
            yield_outcome()(
              [ "$1" = "" ] && echo "Missing key (first argument)" && return 1
              [ "$3" != "" ] && echo "Too many arguments (expected 1 or 2)" && return 2
              command -v base64 >/dev/null || ( echo "Missing command: base64" && return 3 )
              _pipe()(
                encodedKey="$1"
                while read -r data; do
                  echo "##grana[yield-outcome-b64-chunk $encodedKey $data]##"
                done
                echo "##grana[yield-outcome-b64-end $encodedKey]##"
              )
              encodedKey=$( printf "%s" "$1" | base64 | tr -d '\n' )
              if [ "$2" = "" ]; then
                base64 </dev/stdin | _pipe "$encodedKey"
              else
                printf "%s" "$2" | base64 | _pipe "$encodedKey"
              fi
              return 0
            )
            skip(){
              echo "##grana[skip]##"
              exit 0
            }
        """
    ).lstrip()

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self._outcomes_base64_chunks: t.Dict[str, t.List[str]] = collections.defaultdict(list)

    @classmethod
    def _decode_base64_string(cls, data: str) -> str:
        return base64.b64decode(data, validate=True).decode()

    def _process_service_message_expression(self, expression: str) -> None:
        try:
            expression_type, *encoded_args = expression.split()
            if expression_type == "skip":
                self.skip()
            elif expression_type == "yield-outcome-b64-chunk":
                key, value = encoded_args
                self._outcomes_base64_chunks[key].append(value)
            elif expression_type == "yield-outcome-b64-end":
                (encoded_key,) = encoded_args
                encoded_outcome_value: str = "".join(self._outcomes_base64_chunks.pop(encoded_key))
                self.yield_outcome(
                    key=self._decode_base64_string(encoded_key),
                    value=self._decode_base64_string(encoded_outcome_value),
                )
            else:
                raise ValueError(f"Unrecognized expression: {expression!r}")
        except ActionSkip:  # pylint: disable=try-except-raise
            raise
        except Exception:
            self.logger.warning("Failed while parsing system message", exc_info=True)

    def say(self, message: str) -> None:
        # Do not check stderr
        if isinstance(message, Stderr):
            super().say(message)
            return
        memorized_prefix: str = ""
        for line in message.splitlines():
            # `endswith` is a cheaper check than re.findall
            if not line.endswith("]##") or not (matches := self._SERVICE_MESSAGES_SCAN_PATTERN.findall(line)):
                super().say(memorized_prefix + line)
                memorized_prefix = ""
                continue
            for preceding_content, expression in matches:
                memorized_prefix += preceding_content
                self._process_service_message_expression(expression)
        # Do not forget to report system message prefix, if any
        if memorized_prefix:
            super().say(memorized_prefix)
