# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name

from grana.actions.base import ActionBase, CommunicatorPrivilegeError
from grana.display.types import DisplayEvent, DisplayEventName


class Action(ActionBase):

    async def run(self) -> None:
        try:
            self._communicator.get_templar({})
        except CommunicatorPrivilegeError:
            pass
        else:
            self.fail("Must have failed due calling privileged method `get_templar`")
        try:
            self._communicator.send_display_event(DisplayEvent(DisplayEventName.ON_ACTION_START))
        except CommunicatorPrivilegeError:
            pass
        else:
            self.fail("Must have failed due calling privileged method `send_display_event`")
