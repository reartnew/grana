# pylint: disable=missing-module-docstring,missing-class-docstring
from grana import ActionBase, ArgsBase


class DebugArgs(ArgsBase):
    message: str


class Action(ActionBase):
    args: DebugArgs

    async def run(self) -> None:
        self.emit(f"I am {self.args.message!r} too!")
