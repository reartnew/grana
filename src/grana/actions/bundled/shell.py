# pylint: disable=invalid-field-call
"""Separate module for shell-related action"""

import contextlib
import dataclasses
import functools
import os
import pathlib
import shlex
import typing as t
from asyncio.streams import StreamReader
from asyncio.subprocess import create_subprocess_shell, Process  # noqa
from subprocess import PIPE  # nosec

from ..base import ArgsBase, StandardStreamsActionBase, CaptureStream, StreamCaptureConfiguration
from ...config.constants import C

__all__ = [
    "ShellAction",
]


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


class ShellAction(StandardStreamsActionBase):
    """Runs a shell command on the local system."""

    _BYTES_LINE_SEPARATOR: bytes = os.linesep.encode()
    _ENCODING: str = "utf-8"
    args: t.Union[ShellArgsByCommand, ShellArgsByFile]

    @functools.cache
    def _get_capture_configration(self) -> StreamCaptureConfiguration:
        return StreamCaptureConfiguration.from_stream_list(self.args.capture)

    @classmethod
    async def _read_stream(cls, stream: StreamReader, strip_linesep: bool = True) -> t.AsyncGenerator[str, None]:
        async for chunk in stream:  # type: bytes
            if strip_linesep:
                chunk = chunk.rstrip(cls._BYTES_LINE_SEPARATOR)
            yield chunk.decode(cls._ENCODING)

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
