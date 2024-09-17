# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name
from grana import ActionBase


class Action(ActionBase):

    async def run(self) -> None:
        self.disable()
