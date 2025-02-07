"""Check extension possibilities"""

from grana import ActionBase
from grana.loader.default import DefaultYAMLWorkflowLoader
from external_test_lib.constant import TEST_SUFFIX  # type: ignore  # pylint: disable=wrong-import-order


class StringReturningAction(ActionBase):
    """Returns not none"""

    async def run(self) -> str:  # type: ignore
        """Just return something that's not None"""
        return f"I am a string! {TEST_SUFFIX}"


class WorkflowLoader(DefaultYAMLWorkflowLoader):
    """With returning strings"""

    def get_action_factories_mapping(self) -> dict[str, type[ActionBase]]:
        return {
            **super().get_action_factories_mapping(),
            "return-string": StringReturningAction,
        }
