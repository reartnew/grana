"""Check extension possibilities"""

from grana import ArgsBase, ActionBase
from grana.loader.default import DefaultYAMLWorkflowLoader


class ReservedArgs(ArgsBase):
    """Use reserved name"""

    name: str


class BadEchoAction(ActionBase):
    """Reserved args"""

    args: ReservedArgs

    async def run(self) -> None:
        """Do nothing"""


class WorkflowLoader(DefaultYAMLWorkflowLoader):
    """With bad action"""

    def get_action_factories_info(self) -> dict[str, tuple[type[ActionBase], str]]:
        return {
            **super().get_action_factories_info(),
            "echo": (BadEchoAction, "tests-extra"),
        }
