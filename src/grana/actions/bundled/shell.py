"""Separate module for shell-related action"""

import asyncio
import os
import typing as t

from async_shell import Shell, ShellResult

from ..base import ArgsBase, EmissionScannerActionBase
from ..types import Stderr
from ...config.constants import C

__all__ = [
    "ShellArgs",
    "ShellAction",
]


class ShellArgs(ArgsBase):
    """Args for shell-related actions"""

    command: t.Optional[str] = None
    file: t.Optional[str] = None
    environment: t.Optional[t.Dict[str, str]] = None
    cwd: t.Optional[str] = None

    def __post_init__(self) -> None:
        if self.command is None and self.file is None:
            raise ValueError("Neither command nor file specified")
        if self.command is not None and self.file is not None:
            raise ValueError("Both command and file specified")


class ShellAction(EmissionScannerActionBase):
    """Shell commands handler"""

    args: ShellArgs

    async def _read_stdout(self, shell_process: Shell) -> None:
        async for line in shell_process.read_stdout():
            self.emit(line)

    async def _read_stderr(self, shell_process: Shell) -> None:
        async for line in shell_process.read_stderr():
            self.emit(Stderr(line))

    async def _create_shell(self) -> Shell:
        command: str = self.args.command or f"source '{self.args.file}'"
        if C.SHELL_INJECT_YIELD_FUNCTION:
            command = f"{self._SHELL_SERVICE_FUNCTIONS_DEFINITIONS}\n{command}"
        environment: t.Optional[t.Dict[str, str]] = None
        if self.args.environment is not None:
            environment = os.environ.copy()
            environment.update(self.args.environment)
        return Shell(
            command=command,
            environment=environment,
            cwd=self.args.cwd,
        )

    async def run(self) -> None:
        async with await self._create_shell() as shell_process:
            tasks: t.List[asyncio.Task] = [
                asyncio.create_task(self._read_stdout(shell_process)),
                asyncio.create_task(self._read_stderr(shell_process)),
            ]
            # Wait for all tasks to complete
            await asyncio.wait(tasks)
            # Check exceptions
            await asyncio.gather(*tasks)
            result: ShellResult = await shell_process
            if result.code:
                self.fail(f"Exit code: {result.code}")
