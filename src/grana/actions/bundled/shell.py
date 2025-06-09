# pylint: disable=invalid-field-call
"""Separate module for shell-related action"""

import asyncio
import contextlib
import dataclasses
import enum
import functools
import os
import pathlib
import shlex
import typing as t
from asyncio.streams import StreamReader
from asyncio.subprocess import create_subprocess_shell, Process  # noqa
from subprocess import PIPE  # nosec

from ..base import ArgsBase, EmissionScannerActionBase
from ..types import Stderr
from ...config.constants import C

__all__ = [
    "ShellAction",
    "StreamCaptureConfiguration",
    "CaptureStream",
]


@dataclasses.dataclass
class StreamCaptureConfiguration:
    """Configuration for capturing stream data"""

    pass_stdout: bool
    pass_stderr: bool
    capture_stdout: bool
    capture_stderr: bool


class CaptureStream(enum.Enum):
    """Valid values to use in the `capture` argument"""

    STDOUT = "stdout"
    STDERR = "stderr"
    STDOUT_PASS = "stdout+pass"
    STDERR_PASS = "stderr+pass"


class ShellArgsByCommand(ArgsBase):
    """Args for shell-related actions with a command provided"""

    command: str
    environment: t.Optional[dict[str, str]] = None
    cwd: t.Optional[str] = None
    executable: t.Optional[str] = None
    capture: list[CaptureStream] = dataclasses.field(default_factory=list)


class ShellArgsByFile(ArgsBase):
    """Args for shell-related actions with a file provided"""

    file: pathlib.Path
    environment: t.Optional[dict[str, str]] = None
    cwd: t.Optional[str] = None
    executable: t.Optional[str] = None
    capture: list[CaptureStream] = dataclasses.field(default_factory=list)


class ShellAction(EmissionScannerActionBase):
    """Runs a shell command on the local system."""

    _BYTES_LINE_SEPARATOR: bytes = os.linesep.encode()
    _ENCODING: str = "utf-8"
    args: t.Union[ShellArgsByCommand, ShellArgsByFile]

    @functools.cache
    def _get_capture_configration(self) -> StreamCaptureConfiguration:
        if len(self.args.capture) != len(set(self.args.capture)):
            raise ValueError(f"Duplicate capture arguments provided: {self.args.capture}")
        if CaptureStream.STDOUT in self.args.capture and CaptureStream.STDOUT_PASS in self.args.capture:
            raise ValueError(f"{CaptureStream.STDOUT} and {CaptureStream.STDOUT_PASS} are mutually exclusive")
        if CaptureStream.STDERR in self.args.capture and CaptureStream.STDERR_PASS in self.args.capture:
            raise ValueError(f"{CaptureStream.STDERR} and {CaptureStream.STDERR_PASS} are mutually exclusive")
        return StreamCaptureConfiguration(
            capture_stdout=CaptureStream.STDOUT in self.args.capture or CaptureStream.STDOUT_PASS in self.args.capture,
            capture_stderr=CaptureStream.STDERR in self.args.capture or CaptureStream.STDERR_PASS in self.args.capture,
            pass_stdout=CaptureStream.STDOUT not in self.args.capture,
            pass_stderr=CaptureStream.STDERR not in self.args.capture,
        )

    @classmethod
    async def _read_stream(cls, stream: StreamReader, strip_linesep: bool = True) -> t.AsyncGenerator[str, None]:
        async for chunk in stream:  # type: bytes
            if strip_linesep:
                chunk = chunk.rstrip(cls._BYTES_LINE_SEPARATOR)
            yield chunk.decode(cls._ENCODING)

    async def _read_stdout(self, process: Process) -> None:
        if process.stdout is None:
            raise ValueError("Process standard output is not available")
        config: StreamCaptureConfiguration = self._get_capture_configration()
        captured_data: list[str] = []
        async for line in self._read_stream(process.stdout):
            if config.capture_stdout:
                captured_data.append(line)
            if config.pass_stdout:
                self.say(line)
        if config.capture_stdout:
            self.yield_outcome(CaptureStream.STDOUT.value, "\n".join(captured_data))

    async def _read_stderr(self, process: Process) -> None:
        if process.stderr is None:
            raise ValueError("Process standard output is not available")
        config: StreamCaptureConfiguration = self._get_capture_configration()
        captured_data: list[str] = []
        async for line in self._read_stream(process.stderr):
            if config.capture_stderr:
                captured_data.append(line)
            if config.pass_stderr:
                self.say(Stderr(line))
        if config.capture_stderr:
            self.yield_outcome(CaptureStream.STDERR.value, "\n".join(captured_data))

    async def _create_process(self) -> Process:
        command: str
        if isinstance(self.args, ShellArgsByCommand):
            command = self.args.command
        else:
            command = f". {shlex.quote(str(self.args.file))}"
        if C.SHELL_INJECT_YIELD_FUNCTION:
            command = f"{self._SHELL_SERVICE_FUNCTIONS_DEFINITIONS}\n{command}"
        environment: t.Optional[dict[str, str]] = None
        if self.args.environment is not None:
            environment = os.environ.copy()
            environment.update(self.args.environment)
        process = await create_subprocess_shell(
            cmd=command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            env=environment,
            cwd=self.args.cwd,
            executable=self.args.executable or C.DEFAULT_SHELL_EXECUTABLE,
            limit=C.SUBPROCESS_STREAM_BUFFER_LIMIT,
        )
        return process

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

    async def _transmit_process_standard_streams(self, process: Process) -> None:
        tasks: list[asyncio.Task] = [
            asyncio.create_task(self._read_stdout(process)),
            asyncio.create_task(self._read_stderr(process)),
        ]
        # Wait for all tasks to complete
        await asyncio.wait(tasks)
        # Check exceptions
        await asyncio.gather(*tasks)

    async def run(self) -> None:
        async with self._control_process_lifecycle() as process:
            await self._transmit_process_standard_streams(process)
            await process.communicate()
            if process.returncode:
                self.fail(f"Exit code: {process.returncode}")
