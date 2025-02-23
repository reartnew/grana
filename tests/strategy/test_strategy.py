"""Common strategy tests"""

import collections
import typing as t

import pytest
import pytest_data_suites

from grana.actions.base import WorkflowActionExecution
from grana.actions.types import ActionStatus
from grana.config.constants import C
from grana.strategy.base import BaseStrategy
from grana.strategy.impl import ExplicitStrategy, SequentialStrategy
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


class ChainFailureData(t.TypedDict):
    """Chain test data"""

    strategy_class: type[BaseStrategy]
    strict: bool


class ChainFailureDataSuite(pytest_data_suites.DataSuite):
    """Chain test data suite"""

    non_strict_explicit = ChainFailureData(strategy_class=ExplicitStrategy, strict=False)
    strict_sequential = ChainFailureData(strategy_class=SequentialStrategy, strict=True)


@ChainFailureDataSuite.parametrize
@pytest.mark.asyncio
async def test_chain_failure(
    strict_failing_workflow: Workflow,
    strategy_class: type[BaseStrategy],
    strict: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chain failing execution"""
    result: list[WorkflowActionExecution] = []
    monkeypatch.setattr(C, "DEPENDENCY_DEFAULT_STRICTNESS", strict)
    strategy: t.AsyncIterable[WorkflowActionExecution] = strategy_class(strict_failing_workflow)
    async for action in strategy:  # type: WorkflowActionExecution
        with pytest.raises(RuntimeError):
            await action.execute()
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
    result: list[WorkflowActionExecution] = []
    strategy: t.AsyncIterable[WorkflowActionExecution] = ExplicitStrategy(strict_skipping_workflow)
    async for action in strategy:  # type: WorkflowActionExecution
        await action.execute()
        result.append(action)
    assert len(result) == 1  # Should not emit more than one action
    assert result[0].status == ActionStatus.SKIPPED
    # Check final states now
    assert all(a.status == ActionStatus.SKIPPED for a in strict_skipping_workflow.values())


def test_non_redefined_name() -> None:
    """Check strategy name collision"""
    with pytest.raises(NameError, match="Strategy named 'explicit' already exists"):
        # pylint: disable=unused-variable
        class NewExplicitStrategy(ExplicitStrategy):
            """Do not define new name"""
