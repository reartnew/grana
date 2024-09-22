"""Check action parsing"""

import asyncio
import typing as t

import pytest

from grana import ActionBase


class StubAction(ActionBase):
    """A stub."""

    MESSAGES = [
        "Foo",
        "Bar",
        "Baz",
    ]

    def __init__(self) -> None:
        super().__init__(name="stub")

    async def run(self):
        for message in self.MESSAGES:
            self.say(message)
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_action_messages_handling():
    """Check messages handling"""
    action = StubAction()
    messages: t.List[str] = []

    async def reader():
        async for message in action.read_messages():
            messages.append(message)

    reader_task = asyncio.create_task(reader())
    await action
    await reader_task
    assert messages == StubAction.MESSAGES


@pytest.mark.asyncio
async def test_action_await_twice():
    """Check multiple awaiting"""
    action = StubAction()
    await action
    await action
