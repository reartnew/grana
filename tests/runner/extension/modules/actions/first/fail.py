# pylint: disable=missing-module-docstring,missing-class-docstring
from grana import ActionBase, ArgsBase


class FailArgs(ArgsBase):
    message: str


class Action(ActionBase):
    args: FailArgs

    async def run(self) -> None:
        self.fail(self.args.message)
