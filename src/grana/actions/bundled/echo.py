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
    """Prints a message to the output."""

    args: EchoArgs

    async def run(self) -> None:
        self.say(self.args.message)
