"""Check extension possibilities"""

from grana import ActionBase
from grana.loader.default import DefaultYAMLWorkflowLoader


class BadEchoAction:
    """No args"""

    async def run(self) -> None:
        """Do nothing"""


class WorkflowLoader(DefaultYAMLWorkflowLoader):
    """With bad action"""

    def get_action_factories_mapping(self) -> dict[str, type[ActionBase]]:
        return {
            **super().get_action_factories_mapping(),
            "echo": BadEchoAction,  # type: ignore[dict-item]
        }
