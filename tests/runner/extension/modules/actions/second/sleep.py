# pylint: disable=missing-module-docstring,missing-class-docstring
import asyncio

from grana import ActionBase, ArgsBase


class SleepArgs(ArgsBase):
    duration: float


class Action(ActionBase):
    args: SleepArgs

    async def run(self) -> None:
        await asyncio.sleep(self.args.duration)
