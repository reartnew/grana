"""Everything related to a default action interpretation"""

from __future__ import annotations

import asyncio
import base64
import collections
import enum
import functools
import pathlib
import re
import textwrap
import typing as t
from dataclasses import dataclass, fields

import dacite

from .constants import ACTION_RESERVED_FIELD_NAMES
from .types import Stderr, ActionStatus, RenamedMessageSource, NamedMessageSource
from ..display.types import DisplayEvent, DisplayEventName
from ..exceptions import ActionRunError, ActionRenderError, ActionArgumentsLoadError
from ..logging import WithLogger, context
from ..rendering import Templar
from ..tools.concealment import represent_object_type
from ..tools.inspect import get_class_annotations

__all__ = [
    "ActionDependency",
    "ActionSeverity",
    "ActionBase",
    "WorkflowActionExecution",
    "ActionSkip",
    "ArgsBase",
    "EmissionScannerActionBase",
]


# pylint: disable=unused-argument
class AbstractExecutionCommunicator(WithLogger):
    """Communication shim between action and its execution unit"""

    def send_say(self, message: str) -> None:
        """Pass a message to the execution"""
        self.logger.warning("`say` did not take effect")

    def send_yield_outcome(self, key: str, value: t.Any) -> None:
        """Pass an outcome to the execution"""
        self.logger.warning("`yield_outcome` did not take effect")

    def resend_display_event(self, event: DisplayEvent) -> None:
        """Pass a display event to the execution"""
        self.logger.warning("`send_display_event` did not take effect")


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
        self._communicator: AbstractExecutionCommunicator = AbstractExecutionCommunicator()

    def yield_outcome(self, key: str, value: t.Any) -> None:
        """Report outcome key"""
        self.logger.debug(f"Yielding a key: {key!r}")
        self._communicator.send_yield_outcome(key, value)

    def say(self, message: str) -> None:
        """Send a message to the display"""
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


class WorkflowActionExecution(WithLogger):
    """An action that is executed within a workflow"""

    def __init__(
        self,
        *,
        action_class: type[ActionBase],
        name: str,
        raw_args: dict,
        ancestors: t.Optional[dict[str, ActionDependency]] = None,
        description: t.Optional[str] = None,
        selectable: bool = True,
        severity: ActionSeverity = ActionSeverity.NORMAL,
        templar_factory: t.Optional[t.Callable[[], Templar]] = None,
    ) -> None:
        self.action_class = action_class
        self.name: str = name
        self.raw_args: dict = raw_args
        self.description: t.Optional[str] = description
        self.ancestors: dict[str, ActionDependency] = ancestors or {}
        self.selectable: bool = selectable
        self.templar_factory: t.Optional[t.Callable[[], Templar]] = templar_factory

        self.args_class: type[ArgsBase] = ArgsBase
        self.status: ActionStatus = ActionStatus.PENDING
        self.outcomes: dict[str, t.Any] = {}
        self.enabled: bool = True
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.event_queue: asyncio.Queue[DisplayEvent] = asyncio.Queue()
        self.severity: ActionSeverity = severity
        self._check_action_class_args()

    def _check_action_class_args(self):
        """Validate action class `args` annotation
        and try the simplest loading of the dataclass from the original args map"""
        for mro_class in self.action_class.__mro__:
            if args_class := get_class_annotations(mro_class).get("args"):
                break
        else:
            raise ActionArgumentsLoadError(f"Couldn't find an `args` annotation for class {self.action_class.__name__}")
        self.args_class = args_class
        try:
            dacite.from_dict(
                data_class=self.args_class,
                data=self.raw_args,
                config=dacite.Config(
                    check_types=False,
                    strict=True,
                    strict_unions_match=False,
                ),
            )
        except ValueError as e:
            raise ActionArgumentsLoadError(f"Action {self.name!r}: {e}") from e
        except dacite.MissingValueError as e:
            raise ActionArgumentsLoadError(f"Missing key for action {self.name!r}: {e.field_path!r}") from e
        except dacite.UnexpectedDataError as e:
            raise ActionArgumentsLoadError(f"Unrecognized keys for action {self.name!r}: {sorted(e.keys)}") from e

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, status={self.status.value})"

    @functools.lru_cache()
    def compose_nested_source(self, origin: NamedMessageSource) -> NamedMessageSource:
        """Make a nested event"""
        return RenamedMessageSource(name=f"{self.name}/{origin.name}", origin=origin)

    async def _run_with_log_context(self) -> None:
        self.logger.info(f"Running action: {self.name!r}")
        execution = self

        class Communicator(AbstractExecutionCommunicator):
            """Closure-based communication interface"""

            def resend_display_event(self, event: DisplayEvent) -> None:
                new_event = DisplayEvent(name=event.name, **event.kwargs)
                new_event.future.add_done_callback(lambda _: event.future.set_result(None))
                if event.name == DisplayEventName.ON_RUNNER_START:
                    new_event.kwargs["children"] = map(execution.compose_nested_source, event.kwargs["children"])
                elif event.name in (
                    DisplayEventName.ON_ACTION_START,
                    DisplayEventName.ON_ACTION_FINISH,
                    DisplayEventName.ON_ACTION_MESSAGE,
                    DisplayEventName.ON_ACTION_ERROR,
                ):
                    new_event.kwargs["source"] = execution.compose_nested_source(event.kwargs["source"])
                elif event.name not in (
                    DisplayEventName.ON_RUNNER_FINISH,
                    DisplayEventName.ON_PLAN_INTERACTION,
                ):
                    # Just in case we add some event types later and not specify behaviour here
                    raise ValueError(f"Unknown event name: {event.name!r}")  # pragma: no cover
                execution.event_queue.put_nowait(new_event)

            def send_say(self, message: str) -> None:
                execution.event_queue.put_nowait(
                    DisplayEvent(
                        DisplayEventName.ON_ACTION_MESSAGE,
                        source=execution,
                        message=message,
                    )
                )

            def send_yield_outcome(self, key: str, value: t.Any) -> None:
                execution.outcomes[key] = value

        action_instance: ActionBase = self.action_class()
        action_instance._communicator = Communicator()  # pylint: disable=protected-access
        with context(action=self.name):
            # Inject args
            action_instance.args = self.render_action_args()
            return await action_instance.run()

    def render_action_args(self) -> ArgsBase:
        """Prepare action to execution by rendering its template fields"""
        if self.templar_factory is None:
            return ArgsBase()

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

    async def execute(self) -> None:
        """Wraps a call for the underlying action `run` method"""
        self.status = ActionStatus.RUNNING
        try:
            run_result = await self._run_with_log_context()  # type: ignore[func-returns-value]
        except ActionSkip:
            self.skip_execution()
        except Exception as e:
            self.status = ActionStatus.FAILURE if self.severity == ActionSeverity.NORMAL else ActionStatus.WARNING
            self.logger.info(f"Action {self.name!r} failed: {repr(e)}")
            self.future.set_exception(e)
            raise
        else:
            if run_result is not None:
                self.logger.warning(f"Action {self.name!r} return type is {type(run_result)} (not NoneType)")
            self.status = ActionStatus.SUCCESS
            self.future.set_result(None)

    def skip_execution(self) -> None:
        """Skipping the action properly"""
        self.status = ActionStatus.SKIPPED
        self.future.set_result(None)
        self.logger.info(f"Action {self.name!r} skipped")

    def omit_execution(self) -> None:
        """Omitting the action properly"""
        self.status = ActionStatus.OMITTED
        self.future.set_result(None)
        self.logger.info(f"Action {self.name!r} omitted")

    async def read_messages(self) -> t.AsyncGenerator[DisplayEvent, None]:
        """Obtain all said messages sequentially"""
        while True:
            # Wait for either an event or action finish
            queue_getter = asyncio.create_task(self.event_queue.get())
            await asyncio.wait(
                [self.future, queue_getter],
                return_when=asyncio.FIRST_COMPLETED,
            )
            if queue_getter.done():
                yield queue_getter.result()
            if self.future.done():
                # The action is done, so we should drain the queue.
                # Prevent queue from async get since then.
                queue_getter.cancel()
                while True:
                    try:
                        yield self.event_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                return


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
