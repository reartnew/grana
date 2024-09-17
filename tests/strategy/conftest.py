"""Loose strategy helpers"""

# pylint: disable=redefined-outer-name

import typing as t

import pytest

from grana.actions.base import ActionBase, ActionDependency
from grana.workflow import Workflow


def _make_chained_workflow(action_class: t.Type[ActionBase]) -> Workflow:
    step_names: t.List[str] = [
        "foo",
        "bar",
        "baz",
        "qux",
        "fred",
        "thud",
    ]
    return Workflow(
        {
            step_name: action_class(
                name=step_name,
                ancestors={step_names[num - 1]: ActionDependency(strict=True)} if num else {},
            )
            for num, step_name in enumerate(step_names)
        }
    )


@pytest.fixture
def strict_successful_workflow() -> Workflow:
    """Minimalistic strict chained workflow"""

    class SuccessAction(ActionBase):
        """Does nothing"""

        async def run(self) -> None:
            pass

    return _make_chained_workflow(action_class=SuccessAction)


@pytest.fixture
def strict_failing_workflow() -> Workflow:
    """Minimalistic strict chained workflow with failures"""

    class FailingAction(ActionBase):
        """Raises RuntimeError"""

        async def run(self) -> None:
            raise RuntimeError

    return _make_chained_workflow(action_class=FailingAction)


@pytest.fixture
def strict_skipping_workflow() -> Workflow:
    """Minimalistic strict chained workflow with explicit skipping"""

    class SkippingAction(ActionBase):
        """Raises RuntimeError"""

        async def run(self) -> None:
            self.skip()

    return _make_chained_workflow(action_class=SkippingAction)
