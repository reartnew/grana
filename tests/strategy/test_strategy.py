"""Common strategy tests"""

import collections
import typing as t

import pytest

from grana import ActionBase, LooseStrategy, StrictSequentialStrategy
from grana.actions.base import ActionStatus
from grana.strategy import BaseStrategy
from grana.workflow import Workflow


@pytest.mark.asyncio
async def test_chain_success(strict_successful_workflow: Workflow) -> None:
    """Chain successful execution"""
    result: t.List[ActionBase] = []
    strategy: t.AsyncIterable[ActionBase] = LooseStrategy(strict_successful_workflow)
    async for action in strategy:  # type: ActionBase
        await action
        result.append(action)
    assert len(result) == 6  # Should emit all actions
    assert all(action.status == ActionStatus.SUCCESS for action in result)


@pytest.mark.parametrize("strategy_class", [LooseStrategy, StrictSequentialStrategy])
@pytest.mark.asyncio
async def test_chain_failure(strict_failing_workflow: Workflow, strategy_class: t.Type[BaseStrategy]) -> None:
    """Chain failing execution"""
    result: t.List[ActionBase] = []
    strategy: t.AsyncIterable[ActionBase] = strategy_class(strict_failing_workflow)
    async for action in strategy:  # type: ActionBase
        with pytest.raises(RuntimeError):
            await action
        result.append(action)
    assert len(result) == 1  # Should not emit more than one action
    assert result[0].status == ActionStatus.FAILURE
    # Check final states now
    assert collections.Counter(a.status for a in strict_failing_workflow.values()) == {
        ActionStatus.FAILURE: 1,
        ActionStatus.SKIPPED: 5,
    }


@pytest.mark.asyncio
async def test_chain_skip(strict_skipping_workflow: Workflow) -> None:
    """Chain skipping execution"""
    result: t.List[ActionBase] = []
    strategy: t.AsyncIterable[ActionBase] = LooseStrategy(strict_skipping_workflow)
    async for action in strategy:  # type: ActionBase
        await action
        result.append(action)
    assert len(result) == 1  # Should not emit more than one action
    assert result[0].status == ActionStatus.SKIPPED
    # Check final states now
    assert all(a.status == ActionStatus.SKIPPED for a in strict_skipping_workflow.values())


def test_non_redefined_name() -> None:
    """Check strategy name collision"""
    with pytest.raises(NameError, match="Strategy named 'loose' already exists"):
        # pylint: disable=unused-variable
        class NewLooseStrategy(LooseStrategy):
            """Do not define new name"""
