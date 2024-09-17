"""Simple printer"""

from ..base import ArgsBase, ActionBase

__all__ = [
    "EchoAction",
    "EchoArgs",
]


class EchoArgs(ArgsBase):
    """Echo arguments"""

    message: str


class EchoAction(ActionBase):
    """Simple printer"""

    args: EchoArgs

    async def run(self) -> None:
        self.emit(self.args.message)
