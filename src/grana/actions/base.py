"""Everything related to a default action interpretation"""

from __future__ import annotations

import asyncio
import base64
import collections
import enum
import re
import textwrap
import typing as t
import pathlib
from dataclasses import dataclass, fields

import dacite

from ..tools.concealment import represent_object_type
from .constants import ACTION_RESERVED_FIELD_NAMES
from .types import Stderr, OutcomeStorageType, ActionStatus
from ..display.types import DisplayEvent, DisplayEventName
from ..exceptions import ActionRunError, ActionRenderError
from ..logging import WithLogger, context

__all__ = [
    "ActionDependency",
    "ActionSeverity",
    "ActionBase",
    "ActionExecution",
    "ActionSkip",
    "ArgsBase",
    "EmissionScannerActionBase",
]


class AbstractExecutionCommunicator:
    """aaa"""

    def send_say(self, message: str) -> None:
        """Pass a message to the execution"""
        raise NotImplementedError

    def send_yield_outcome(self, key: str, value: t.Any) -> None:
        """Pass an outcome to the execution"""
        raise NotImplementedError

    def send_display_event(self, event: DisplayEvent) -> None:
        """Pass a display event to the execution"""
        raise NotImplementedError


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
        reserved_names_collisions: set[str] = {f.name for f in fields(sub_dataclass)} & ACTION_RESERVED_FIELD_NAMES
        if reserved_names_collisions:
            raise TypeError(f"Reserved names found in {name!r} class definition: {sorted(reserved_names_collisions)}")
        return sub_dataclass


@dataclass
class ArgsBase(metaclass=ArgsMeta):
    """Default empty args holder.
    Should be subclassed and then added to the `args` annotation of any action class."""


class ActionBase(WithLogger):
    """Base class for all actions"""

    args: ArgsBase

    def __init__(self) -> None:
        self._communicator: t.Optional[AbstractExecutionCommunicator] = None

    def yield_outcome(self, key: str, value: t.Any) -> None:
        """Report outcome key"""
        if self._communicator is None:
            self.logger.warning("Communicator is not set, so `yield_outcome` does not take effect")
            return
        self.logger.debug(f"Yielding a key: {key!r}")
        self._communicator.send_yield_outcome(key, value)

    def say(self, message: str) -> None:
        """Send a message to the display"""
        if self._communicator is None:
            self.logger.warning("Communicator is not set, so `say` does not take effect")
            return
        self._communicator.send_say(message)

    def skip(self) -> t.NoReturn:
        """Set status to SKIPPED and stop execution"""
        raise ActionSkip

    def fail(self, message: str = "") -> t.NoReturn:
        """Set corresponding error message and raise an exception"""
        raise ActionRunError(message)

    async def run(self) -> None:
        """Main entry to be implemented in subclasses"""
        raise NotImplementedError


class ActionExecution(WithLogger):
    """An action that is executed within a workflow"""

    def __init__(
        self,
        *,
        action_class: type[ActionBase],
        args_class: type[ArgsBase],
        name: str,
        raw_args: dict,
        ancestors: t.Optional[dict[str, ActionDependency]] = None,
        description: t.Optional[str] = None,
        selectable: bool = True,
        severity: ActionSeverity = ActionSeverity.NORMAL,
    ) -> None:
        self.action_class = action_class
        self.args_class = args_class
        self.name: str = name
        self.raw_args: dict = raw_args
        self.description: t.Optional[str] = description
        self.ancestors: dict[str, ActionDependency] = ancestors or {}
        self.selectable: bool = selectable
        self.templar_factory = None

        self.outcomes: OutcomeStorageType = {}
        self._status: ActionStatus = ActionStatus.PENDING
        self._enabled: bool = True
        # Do not create asyncio-related objects on constructing object to decouple from the event loop
        self._maybe_finish_flag: t.Optional[asyncio.Future] = None
        self._maybe_message_queue: t.Optional[asyncio.Queue[DisplayEvent]] = None
        self._running_task: t.Optional[asyncio.Task] = None
        self._severity: ActionSeverity = severity

    def set_templar_factory(self, factory):
        self.templar_factory = factory

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

    async def _run_with_log_context(self) -> None:
        self.logger.info(f"Running action: {self.name!r}")
        execution = self

        class Communicator(AbstractExecutionCommunicator):

            def send_display_event(self, event: DisplayEvent) -> None:
                execution._event_queue.put_nowait(event)

            def send_say(self, message: str) -> None:
                self.send_display_event(
                    DisplayEvent(
                        DisplayEventName.ON_ACTION_MESSAGE,
                        source=execution,
                        message=message,
                    )
                )

            def send_yield_outcome(self, key: str, value: t.Any) -> None:
                execution.outcomes[key] = value

        action_instance: ActionBase = self.action_class()
        action_instance._communicator = Communicator()
        with context(action=self.name):
            # Inject args
            action_instance.args = self.render_action_args()
            return await action_instance.run()

    def render_action_args(self) -> ArgsBase:
        """Prepare action to execution by rendering its template fields"""
        templar = self.templar_factory()

        rendered_args_dict: dict = templar.recursive_render(self.raw_args)
        try:
            parsed_args: ArgsBase = t.cast(
                ArgsBase,
                dacite.from_dict(
                    data_class=self.args_class,
                    data=rendered_args_dict,
                    config=dacite.Config(
                        check_types=True,
                        strict=True,
                        strict_unions_match=True,
                        cast=[enum.Enum, pathlib.Path],
                    ),
                ),
            )
        except dacite.WrongTypeError as e:
            raise ActionRenderError(
                f"Unrecognized {e.field_path!r} content type: {represent_object_type(e.value)}"
                f" (expected {e.field_type!r})"
            ) from None
        return parsed_args

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
            self._internal_skip()
        except Exception as e:
            self._internal_fail(e)
            raise
        else:
            self._status = ActionStatus.SUCCESS
        if not fut.done():
            fut.set_result(None)

    def _internal_skip(self) -> None:
        self._status = ActionStatus.SKIPPED
        self.get_future().set_result(None)
        self.logger.info(f"Action {self.name!r} skipped")

    def _internal_omit(self) -> None:
        self._status = ActionStatus.OMITTED
        self.get_future().set_result(None)
        self.logger.info(f"Action {self.name!r} omitted")

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

    def __init__(self) -> None:
        super().__init__()
        self._outcomes_base64_chunks: dict[str, list[str]] = collections.defaultdict(list)

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
