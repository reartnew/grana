"""Check isolated action"""

import asyncio

import pytest

from grana.actions.base import ActionBase, CommunicatorPrivilegeError
from grana.display.types import DisplayEvent, DisplayEventName


class StubAction(ActionBase):
    """A stub."""

    MESSAGES = [
        "Foo",
        "Bar",
        "Baz",
    ]

    async def run(self):
        for message in self.MESSAGES:
            self.say(message)
            self.yield_outcome(key=message, value=message)
            self._communicator.resend_display_event(
                DisplayEvent(
                    name=DisplayEventName.ON_ACTION_MESSAGE,
                    message="foo",
                )
            )
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_action_standalone_run():
    """Check standalone action run"""
    action = StubAction()
    with pytest.raises(CommunicatorPrivilegeError):
        await action.run()
