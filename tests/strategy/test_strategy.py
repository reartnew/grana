"""Common strategy tests"""

import typing as t

import pytest

from grana.actions.base import WorkflowActionExecution
from grana.actions.types import ActionStatus
from grana.strategy.impl import ExplicitStrategy
from grana.workflow import Workflow


@pytest.mark.asyncio
async def test_chain_success(strict_successful_workflow: Workflow) -> None:
    """Chain successful execution"""
    result: list[WorkflowActionExecution] = []
    strategy: t.AsyncIterable[WorkflowActionExecution] = ExplicitStrategy(strict_successful_workflow)
    async for action in strategy:  # type: WorkflowActionExecution
        await action.execute()
        result.append(action)
    assert len(result) == 6  # Should emit all actions
    assert all(action.status == ActionStatus.SUCCESS for action in result)


def test_non_redefined_name() -> None:
    """Check strategy name collision"""
    with pytest.raises(NameError, match="Strategy named 'explicit' already exists"):
        # pylint: disable=unused-variable
        class NewExplicitStrategy(ExplicitStrategy):
            """Do not define new name"""
