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

    @classmethod
    def get_action_factories_info(cls) -> dict[str, tuple[type[ActionBase], str]]:
        return {
            **super().get_action_factories_info(),
            "return-string": (StringReturningAction, "tests-extra"),
        }
