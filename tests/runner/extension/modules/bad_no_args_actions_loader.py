"""Check extension possibilities"""

from grana import ActionBase
from grana.loader.default import DefaultYAMLWorkflowLoader


class BadEchoAction:
    """No args"""

    async def run(self) -> None:
        """Do nothing"""


class WorkflowLoader(DefaultYAMLWorkflowLoader):
    """With bad action"""

    def get_action_factories_info(self) -> dict[str, tuple[type[ActionBase], str]]:
        return {
            **super().get_action_factories_info(),
            "echo": (BadEchoAction, "tests-extra"),  # type: ignore[dict-item]
        }
