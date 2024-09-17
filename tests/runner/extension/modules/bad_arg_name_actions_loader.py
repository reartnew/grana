"""Check extension possibilities"""

from grana import ArgsBase
from grana.loader.default import DefaultYAMLWorkflowLoader


class ReservedArgs(ArgsBase):
    """Use reserved name"""

    name: str


class BadEchoAction:
    """Reserved args"""

    args: ReservedArgs

    async def run(self) -> str:
        """Just check return"""
        return f"I am a string: {self.args.name}"


class WorkflowLoader(DefaultYAMLWorkflowLoader):
    """Able to build echoes"""

    STATIC_ACTION_FACTORIES = {
        **DefaultYAMLWorkflowLoader.STATIC_ACTION_FACTORIES,
        "echo": BadEchoAction,  # type: ignore
    }
