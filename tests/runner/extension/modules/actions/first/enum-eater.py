# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name
from enum import Enum

from grana import ActionBase, ArgsBase


class Arg(Enum):
    FOO = "Foo"
    BAR = "Bar"


class EnumEaterArgs(ArgsBase):
    food: Arg


class Action(ActionBase):
    args: EnumEaterArgs

    async def run(self) -> None:
        assert self.args.food in (Arg.FOO, Arg.BAR)
