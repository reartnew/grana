"""Everything related to a default action interpretation"""

from __future__ import annotations

import asyncio
import base64
import collections
import contextlib
import copy
import dataclasses
import enum
import functools
import re
import textwrap
import typing as t
from asyncio.streams import StreamReader
from asyncio.subprocess import Process  # noqa

from .constants import ACTION_RESERVED_FIELD_NAMES
from .types import Stderr, ActionStatus, RenamedMessageSource, NamedMessageSource
from ..display.types import DisplayEvent, DisplayEventName
from ..exceptions import ActionRunError, ActionRenderError, ActionArgumentsLoadError
from ..logging import WithLogger, context
from ..rendering import CommonTemplar
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
    "StandardStreamsActionBase",
    "CommunicatorPrivilegeError",
    "StreamCaptureConfiguration",
    "CaptureStream",
    "SubprocessActionBase",
]


class CommunicatorPrivilegeError(Exception):
    """Raised when an unprivileged action is calling a privileged communicator method."""


# pylint: disable=unused-argument
class AbstractExecutionCommunicator(WithLogger):
    """Communication shim between action and its execution unit"""

    def send_say(self, message: str) -> None:
        """Pass a message to the execution"""
        self.logger.warning("`say` did not take effect")

    def send_yield_outcome(self, key: str, value: t.Any) -> None:
        """Pass an outcome to the execution"""
        self.logger.warning("`yield_outcome` did not take effect")

    def send_display_event(self, event: DisplayEvent) -> None:
        """Pass a display event to the execution"""
        raise NotImplementedError

    def get_templar(self, extra_locals: t.Dict[str, t.Any]) -> CommonTemplar:
        """Build a templar"""
        raise NotImplementedError


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

    def on_render(self) -> None:
        """Hook method, called right after rendering args"""


@dataclasses.dataclass
class WorkflowActionExecution(WithLogger):
    """An action that is executed within a workflow"""

    action_class: type[ActionBase]
    name: str
    raw_args: dict
    templar_factory: t.Callable[[dict], CommonTemplar]
    ancestors: list[ActionDependency] = dataclasses.field(default_factory=list)
    description: t.Optional[str] = None
    selectable: bool = True
    severity: ActionSeverity = ActionSeverity.NORMAL
    locals_map: dict[str, t.Any] = dataclasses.field(default_factory=dict)
    action_instance: t.Optional[ActionBase] = None

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

    @classmethod
    @functools.cache
    def _get_privileged_action_classes(cls) -> t.Set[t.Type[ActionBase]]:
        """Get action classes that receive privileged communicator"""
        from ..loader.default import DefaultYAMLWorkflowLoader

        factories = DefaultYAMLWorkflowLoader.get_action_factories_info()
        return {
            factories[k][0]
            for k in (
                "subflow",
                "loop",
            )
        }

    async def _run_with_log_context(self) -> None:
        self.logger.info(f"Running action: {self.name!r}")
        with context(action=self.name):
            self.action_instance = self.prepare_action_instance()
            await self.action_instance.run()

    def prepare_action_instance(self) -> ActionBase:
        """Make an action instance to run later"""
        execution = self

        class DefaultCommunicator(AbstractExecutionCommunicator):
            """Closure-based communication interface"""

            def send_display_event(self, event: DisplayEvent) -> None:
                self.logger.error("`send_display_event` is privileged")
                raise CommunicatorPrivilegeError

            def get_templar(self, extra_locals: t.Dict[str, t.Any]) -> CommonTemplar:
                self.logger.error("`get_templar` is privileged")
                raise CommunicatorPrivilegeError

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

        class PrivilegedCommunicator(DefaultCommunicator):
            """Closure-based communication interface with privileged methods"""

            def send_display_event(self, event: DisplayEvent) -> None:
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

            def get_templar(self, extra_locals: t.Dict[str, t.Any]) -> CommonTemplar:
                return execution.templar_factory(
                    {
                        **execution.locals_map,
                        **extra_locals,
                    }
                )

        action_instance: ActionBase = self.action_class()
        selected_communicator: AbstractExecutionCommunicator
        if self.action_class in self._get_privileged_action_classes():
            selected_communicator = PrivilegedCommunicator()
        else:
            selected_communicator = DefaultCommunicator()
        action_instance._communicator = selected_communicator  # pylint: disable=protected-access
        # Inject args
        action_instance.args = self._render_action_args()
        # Call the hook
        action_instance.on_render()
        return action_instance

    def _render_action_args(self) -> ArgsBase:
        """Prepare action to execution by rendering its template fields"""
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
class StandardStreamsActionBase(ActionBase):
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

    @functools.cache
    def _get_capture_configration(self) -> StreamCaptureConfiguration:
        return StreamCaptureConfiguration(
            pass_stdout=True,
            pass_stderr=True,
            capture_stdout=False,
            capture_stderr=False,
        )

    async def _read_stdout(self, stream: t.AsyncIterable[str]) -> None:
        config: StreamCaptureConfiguration = self._get_capture_configration()
        captured_data: list[str] = []
        async for line in stream:
            if config.capture_stdout:
                captured_data.append(line)
            if config.pass_stdout:
                self.say(line)
        if config.capture_stdout:
            self.yield_outcome(CaptureStream.STDOUT.value, "".join(captured_data))

    async def _read_stderr(self, stream: t.AsyncIterable[str]) -> None:
        config: StreamCaptureConfiguration = self._get_capture_configration()
        captured_data: list[str] = []
        async for line in stream:
            if config.capture_stderr:
                captured_data.append(line)
            if config.pass_stderr:
                self.say(Stderr(line))
        if config.capture_stderr:
            self.yield_outcome(CaptureStream.STDERR.value, "".join(captured_data))

    async def _start_streams_transmission(
        self,
        stdout: t.AsyncIterable[str],
        stderr: t.AsyncIterable[str],
    ) -> asyncio.Task:
        tasks: list[asyncio.Task] = [
            asyncio.create_task(self._read_stdout(stdout)),
            asyncio.create_task(self._read_stderr(stderr)),
        ]

        async def wait_and_gather():
            # Wait for all tasks to complete
            await asyncio.wait(tasks)
            # Check exceptions
            await asyncio.gather(*tasks)

        return asyncio.create_task(wait_and_gather())


class CaptureStream(enum.Enum):
    """Valid values to use in the `capture` argument"""

    STDOUT = "stdout"
    STDERR = "stderr"
    STDOUT_PASS = "stdout+pass"  # nosec
    STDERR_PASS = "stderr+pass"  # nosec


@dataclasses.dataclass
class StreamCaptureConfiguration:
    """Configuration for capturing stream data"""

    pass_stdout: bool
    pass_stderr: bool
    capture_stdout: bool
    capture_stderr: bool

    @classmethod
    def from_streams_list(cls, spec: list[CaptureStream]) -> StreamCaptureConfiguration:
        """Create a StreamCaptureConfiguration from a list of streams"""
        if len(spec) != len(set(spec)):
            raise ValueError(f"Duplicate capture arguments provided: {spec}")
        if CaptureStream.STDOUT in spec and CaptureStream.STDOUT_PASS in spec:
            raise ValueError(f"{CaptureStream.STDOUT} and {CaptureStream.STDOUT_PASS} are mutually exclusive")
        if CaptureStream.STDERR in spec and CaptureStream.STDERR_PASS in spec:
            raise ValueError(f"{CaptureStream.STDERR} and {CaptureStream.STDERR_PASS} are mutually exclusive")
        return StreamCaptureConfiguration(
            capture_stdout=CaptureStream.STDOUT in spec or CaptureStream.STDOUT_PASS in spec,
            capture_stderr=CaptureStream.STDERR in spec or CaptureStream.STDERR_PASS in spec,
            pass_stdout=CaptureStream.STDOUT not in spec,
            pass_stderr=CaptureStream.STDERR not in spec,
        )


class SubprocessActionBase(StandardStreamsActionBase):
    """Base class for subprocess-based actions"""

    _ENCODING: str = "utf-8"

    @classmethod
    async def _read_stream(cls, stream: StreamReader) -> t.AsyncGenerator[str, None]:
        async for chunk in stream:  # type: bytes
            yield chunk.decode(cls._ENCODING)

    async def _create_process(self) -> Process:
        raise NotImplementedError

    @contextlib.asynccontextmanager
    async def _control_process_lifecycle(self):
        process = await self._create_process()
        yield process
        if process.returncode is None:
            process.kill()
        # Close communication anyway
        await process.communicate()
        for stream in (process.stdout, process.stderr, process.stdin):
            if stream is None:
                continue
            stream._transport.close()  # type: ignore[union-attr]  # pylint: disable=protected-access

    async def run(self) -> None:
        async with self._control_process_lifecycle() as process:
            streams_transmission = await self._start_streams_transmission(
                stdout=self._read_stream(process.stdout),
                stderr=self._read_stream(process.stderr),
            )
            await streams_transmission
            await process.communicate()
            if process.returncode:
                self.fail(f"Exit code: {process.returncode}")
