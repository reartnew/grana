# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name
import typing as t

from grana import ActionBase, ArgsBase


class UnionArgs(ArgsBase):
    message: t.Union[str, t.List[str]]


class Action(ActionBase):
    args: UnionArgs

    async def run(self) -> None:
        self.emit(str(self.args.message))
