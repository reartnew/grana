# pylint: disable=invalid-field-call
"""Separate module for shell-related action"""

import dataclasses
import functools
import os
import pathlib
import shlex
import typing as t
from asyncio.subprocess import create_subprocess_shell, Process  # noqa
from subprocess import PIPE  # nosec

from ..base import ArgsBase, CaptureStream, StreamCaptureConfiguration, SubprocessActionBase
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


class ShellAction(SubprocessActionBase):
    """Runs a shell command on the local system."""

    args: t.Union[ShellArgsByCommand, ShellArgsByFile]

    @functools.cache
    def _get_capture_configration(self) -> StreamCaptureConfiguration:
        return StreamCaptureConfiguration.from_streams_list(self.args.capture)

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
