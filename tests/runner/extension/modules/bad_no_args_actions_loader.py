"""Check extension possibilities"""

from grana.loader.default import DefaultYAMLWorkflowLoader


class BadEchoAction:
    """No args"""

    async def run(self) -> str:
        """Just check return"""
        return "I am a string!"


class WorkflowLoader(DefaultYAMLWorkflowLoader):
    """Able to build echoes"""

    STATIC_ACTION_FACTORIES = {
        **DefaultYAMLWorkflowLoader.STATIC_ACTION_FACTORIES,
        "echo": BadEchoAction,  # type: ignore
    }
