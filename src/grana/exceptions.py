"""All intercepted errors"""

__all__ = [
    "ExecutionFailed",
    "ActionRenderError",
    "PendingActionUnresolvedOutcomeError",
    "ActionRenderRecursionError",
    "RestrictedBuiltinError",
    "ActionRunError",
    "BaseError",
    "LoadError",
    "IntegrityError",
    "SourceError",
    "InteractionError",
    "ActionArgumentsLoadError",
    "YAMLStructureError",
    "AutoStrategyCycleError",
]

import pathlib


class ExecutionFailed(Exception):
    """Some steps failed"""


class ActionRenderError(Exception):
    """Action rendering failed"""


class PendingActionUnresolvedOutcomeError(ActionRenderError):
    """Action rendering failed due to unresolved outcome"""

    def __init__(self, action_name: str):
        self.action_name: str = action_name
        super().__init__(f"Action {action_name!r} has not finished yet, therefore its outcomes are unresolved")


class AutoStrategyCycleError(Exception):
    """Automatic strategy discovered cyclic dependencies"""


class ActionArgumentsLoadError(Exception):
    """Action arguments loading failed"""


class ActionRenderRecursionError(ActionRenderError):
    """Action recursion depth exceeded"""


class RestrictedBuiltinError(Exception):
    """Action rendering access to a restricted builtin function"""


class ActionRunError(Exception):
    """Action execution failed"""


class BaseError(Exception):
    """Common base to catch in CLI"""

    CODE: int = 101


class LoadError(BaseError):
    """Loader regular exception during load process"""

    CODE: int = 102

    def __init__(self, message: str, stack: tuple[pathlib.Path, ...]) -> None:
        self.message: str = message
        self.stack: tuple[pathlib.Path, ...] = stack
        text: str = message
        if stack:
            text += f"\n  Sources stack: {' -> '.join(str(path) for path in stack)}"
        super().__init__(text)


class IntegrityError(BaseError):
    """Workflow structure error"""

    CODE: int = 103


class SourceError(BaseError):
    """Source file not recognized"""

    CODE: int = 104


class InteractionError(BaseError):
    """Can't interact with a display"""

    CODE: int = 105


class YAMLStructureError(BaseError):
    """Custom tags structure error"""

    CODE: int = 106
