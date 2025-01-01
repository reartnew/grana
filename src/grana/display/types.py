"""Types collection"""

import asyncio
import enum

__all__ = [
    "DisplayEventName",
    "DisplayEvent",
]


class DisplayEventName(enum.Enum):
    """Valid event names"""

    ON_ACTION_MESSAGE = "on_action_message"
    ON_ACTION_ERROR = "on_action_error"
    ON_RUNNER_START = "on_runner_start"
    ON_RUNNER_FINISH = "on_runner_finish"
    ON_PLAN_INTERACTION = "on_plan_interaction"
    ON_ACTION_START = "on_action_start"
    ON_ACTION_FINISH = "on_action_finish"


class DisplayEvent:
    """Display-related event floating to the runner"""

    def __init__(self, name: DisplayEventName, **kwargs) -> None:
        self.name: DisplayEventName = name
        self.kwargs: dict = kwargs
        self.future: asyncio.Future = asyncio.Future()
