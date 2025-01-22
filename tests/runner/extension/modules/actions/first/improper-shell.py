# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name
from asyncio.subprocess import Process
from asyncio.subprocess import create_subprocess_shell

from grana import ArgsBase
from grana.actions.bundled.shell import ShellAction


class Action(ShellAction):
    args: ArgsBase  # type: ignore[assignment]

    async def _create_process(self) -> Process:
        return await create_subprocess_shell("while true; do sleep 1; done")

    async def run(self) -> None:
        async with self._control_process_lifecycle() as process:
            try:
                await self._transmit_process_standard_streams(process)
            except ValueError:
                pass
            else:
                self.fail("Must have failed due to missing stdout and stderr pipes")
