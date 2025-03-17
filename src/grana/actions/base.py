"""Everything related to a default action interpretation"""

from __future__ import annotations

import asyncio
import base64
import collections
import copy
import dataclasses
import enum
import functools
import re
import textwrap
import typing as t

from .constants import ACTION_RESERVED_FIELD_NAMES
from .types import Stderr, ActionStatus, RenamedMessageSource, NamedMessageSource
from ..display.types import DisplayEvent, DisplayEventName
from ..exceptions import ActionRunError, ActionRenderError, ActionArgumentsLoadError
from ..logging import WithLogger, context
from ..rendering import WorkflowTemplar
from ..tools import classloader
from ..tools.classloader.exceptions import TypeMatchError, ClassLoaderError
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


def strict_default_factory() -> bool:
    """Get default strictness value"""
    from ..config.constants import C

    return C.DEPENDENCY_DEFAULT_STRICTNESS


@dataclasses.dataclass
class ActionDependency:
    """Dependency info holder"""

    name: str
    strict: bool = dataclasses.field(default_factory=strict_default_factory)


class ArgsMeta(type):
    """Metaclass for args containers that makes them all dataclasses"""

    def __new__(cls, name, bases, dct):
        sub_dataclass = dataclasses.dataclass(super().__new__(cls, name, bases, dct))
        reserved_names_collisions: set[str] = {
            f.name for f in dataclasses.fields(sub_dataclass)
        } & ACTION_RESERVED_FIELD_NAMES
        if reserved_names_collisions:
            raise TypeError(f"Reserved names found in {name!r} class definition: {sorted(reserved_names_collisions)}")
        return sub_dataclass


@dataclasses.dataclass
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


@dataclasses.dataclass
class WorkflowActionExecution(WithLogger):
    """An action that is executed within a workflow"""

    action_class: type[ActionBase]
    name: str
    raw_args: dict
    ancestors: list[ActionDependency] = dataclasses.field(default_factory=list)
    description: t.Optional[str] = None
    selectable: bool = True
    severity: ActionSeverity = ActionSeverity.NORMAL
    templar_factory: t.Optional[t.Callable[[dict], WorkflowTemplar]] = None
    locals_map: dict[str, t.Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        self.args_class: type[ArgsBase] = ArgsBase
        self.status: ActionStatus = ActionStatus.PENDING
        self.outcomes: dict[str, t.Any] = {}
        self.enabled: bool = True
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.event_queue: asyncio.Queue[DisplayEvent] = asyncio.Queue()
        self._check_action_class_args()

    def __hash__(self) -> int:
        return id(self)

    def _check_action_class_args(self):
        """Validate action class `args` annotation
        and try the simplest loading of the dataclass from the original args map"""
        for mro_class in self.action_class.__mro__:
            if args_class := get_class_annotations(mro_class).get("args"):
                break
        else:
            raise ActionArgumentsLoadError(f"Couldn't find an `args` annotation for class {self.action_class.__name__}")
        try:
            self.args_class = classloader.get_data_class_by_data_signature(
                data_type=args_class,
                data=self.raw_args,
            )
        except (ValueError, ClassLoaderError) as e:
            raise ActionArgumentsLoadError(f"Action {self.name!r}: {e}") from e

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, status={self.status.value})"

    @functools.cache
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
                ):  # pragma: no cover
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

        templar = self.templar_factory(self.locals_map)
        fields: t.Dict[str, dataclasses.Field] = {f.name: f for f in dataclasses.fields(self.args_class)}
        rendered_args_dict: dict = {}
        for arg_key, arg_value in self.raw_args.items():
            corr_field: dataclasses.Field = fields[arg_key]
            if corr_field.metadata.get("rendering") == "disabled":
                self.logger.debug(f"Argument {arg_key!r} will not be rendered")
                rendered_args_dict[arg_key] = copy.deepcopy(arg_value)
            else:
                rendered_args_dict[arg_key] = templar.render(arg_value)
        try:
            parsed_args: ArgsBase = classloader.from_dict(
                data_type=self.args_class,
                data=rendered_args_dict,
            )
        except TypeMatchError as e:
            raise ActionRenderError(e) from None
        return parsed_args

    async def execute(self) -> None:
        """Wraps a call for the underlying action `run` method"""
        self.status = ActionStatus.RUNNING
        try:
            run_result = await self._run_with_log_context()  # type: ignore[func-returns-value]
        except ActionSkip:
            self.skip()
        except Exception as e:
            self.status = ActionStatus.FAILURE if self.severity == ActionSeverity.NORMAL else ActionStatus.WARNING
            self.logger.info(f"Action {self.name!r} failed: {repr(e)}")
            self.future.set_result(False)
            raise
        else:
            if run_result is not None:
                self.logger.warning(f"Action {self.name!r} return type is {type(run_result)} (not NoneType)")
            self.status = ActionStatus.SUCCESS
            self.future.set_result(True)

    def skip(self) -> None:
        """Skipping the action properly"""
        self.status = ActionStatus.SKIPPED
        self.future.set_result(True)
        self.logger.info(f"Action {self.name!r} skipped")

    def omit(self) -> None:
        """Omitting the action properly"""
        self.status = ActionStatus.OMITTED
        self.future.set_result(True)
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
                  if [ "$data" != "" ]; then
                    echo "##grana[yield-outcome-b64-chunk $encodedKey $data]##"
                  fi
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
                encoded_outcome_value: str = "".join(self._outcomes_base64_chunks.pop(encoded_key, []))
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
