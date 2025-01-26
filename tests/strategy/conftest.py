"""Explicit strategy helpers"""

# pylint: disable=redefined-outer-name

import pytest_asyncio

from grana.actions.base import (
    ActionExecution,
    ActionDependency,
    ActionBase,
)
from grana.workflow import Workflow


def _make_chained_workflow(action_class: type[ActionBase]) -> Workflow:
    step_names: list[str] = [
        "foo",
        "bar",
        "baz",
        "qux",
        "fred",
        "thud",
    ]
    return Workflow(
        {
            step_name: ActionExecution(
                name=step_name,
                action_class=action_class,
                raw_args={},
                ancestors={step_names[num - 1]: ActionDependency(strict=True)} if num else {},
            )
            for num, step_name in enumerate(step_names)
        }
    )


@pytest_asyncio.fixture
async def strict_successful_workflow() -> Workflow:
    """Minimalistic strict chained workflow"""

    class SuccessAction(ActionBase):
        """Does nothing"""

        async def run(self) -> None:
            pass

    return _make_chained_workflow(action_class=SuccessAction)


@pytest_asyncio.fixture
async def strict_failing_workflow() -> Workflow:
    """Minimalistic strict chained workflow with failures"""

    class FailingAction(ActionBase):
        """Raises RuntimeError"""

        async def run(self) -> None:
            raise RuntimeError

    return _make_chained_workflow(action_class=FailingAction)


@pytest_asyncio.fixture
async def strict_skipping_workflow() -> Workflow:
    """Minimalistic strict chained workflow with explicit skipping"""

    class SkippingAction(ActionBase):
        """Raises RuntimeError"""

        async def run(self) -> None:
            self.skip()

    return _make_chained_workflow(action_class=SkippingAction)
