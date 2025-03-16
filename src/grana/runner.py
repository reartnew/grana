"""
Runner has too many dependencies,
thus placed to a separate module.
"""

import asyncio
import functools
import io
import sys
import typing as t
from pathlib import Path

from . import types
from .actions.base import WorkflowActionExecution
from .actions.types import ActionStatus
from .config.constants import C
from .display.types import DisplayEvent, DisplayEventName
from .exceptions import SourceError, ExecutionFailed, ActionRenderError, ActionRunError
from .loader.helpers import get_default_loader_class_for_source
from .logging import WithLogger
from .workflow import Workflow

__all__ = [
    "Runner",
]

IOType = io.TextIOBase


class Runner(WithLogger):
    """Main entry object"""

    def __init__(self, source: t.Union[Path, IOType, dict, None] = None) -> None:
        self._workflow_source: t.Union[Path, IOType, dict]
        if source is not None:
            self._workflow_source = source
        else:
            self._workflow_source = self._detect_workflow_source()
        self._started: bool = False
        self._execution_failed: bool = False

    @functools.cached_property
    def _events_flow(self) -> asyncio.Queue:
        return asyncio.Queue()

    @functools.cached_property
    def loader(self) -> types.LoaderType:
        """Workflow loader"""
        loader_class: types.LoaderClassType
        if C.WORKFLOW_LOADER_CLASS:
            loader_class = C.WORKFLOW_LOADER_CLASS
        else:
            loader_class = get_default_loader_class_for_source(self._workflow_source)
        self.logger.debug(f"Using workflow loader class: {loader_class}")
        return loader_class()

    @functools.cached_property
    def workflow(self) -> Workflow:
        """Calculated workflow"""
        if isinstance(self._workflow_source, io.TextIOBase):
            return self.loader.load_from_text(self._workflow_source.read())
        if isinstance(self._workflow_source, dict):
            return self.loader.load_from_dict(self._workflow_source)
        return self.loader.load_from_file(self._workflow_source)

    @functools.cached_property
    def display(self) -> types.DisplayType:
        """Attached display"""
        display_class: types.DisplayClassType = C.EXTERNAL_DISPLAY_CLASS or C.INTERNAL_DISPLAY_CLASS
        self.logger.debug(f"Using display class: {display_class}")
        return display_class()

    @classmethod
    def _detect_workflow_source(cls) -> t.Union[Path, IOType]:
        if source_file := C.WORKFLOW_SOURCE_FILE:
            if str(source_file) == "-":
                cls.logger.info("Using stdin as workflow source")
                return t.cast(IOType, sys.stdin)
            if not source_file.exists():
                raise SourceError(f"Given workflow file does not exist: {source_file}")
            cls.logger.info(f"Using given workflow file: {source_file}")
            return source_file
        scan_path: Path = C.CONTEXT_DIRECTORY
        cls.logger.debug(f"Looking for workflow files at {str(scan_path)!r}")
        located_source_file: t.Optional[Path] = None
        for candidate_file_name in (
            "grana.yml",
            "grana.yaml",
        ):  # type: str
            if (maybe_source_file := scan_path / candidate_file_name).exists():
                cls.logger.info(f"Detected the workflow source: {str(maybe_source_file)!r}")
                if located_source_file is not None:
                    raise SourceError(f"Multiple workflow sources detected in {scan_path}")
                located_source_file = maybe_source_file
        if located_source_file is None:
            raise SourceError(f"No workflow source detected in {scan_path}")
        return located_source_file

    def _send_display_event(self, name: DisplayEventName, **kwargs) -> asyncio.Future:
        """Create a display event and return a future which indicates event processing status"""
        self._events_flow.put_nowait(event := DisplayEvent(name, **kwargs))
        return event.future

    async def _process_display_events(self) -> None:
        while True:
            event: DisplayEvent = await self._events_flow.get()
            try:
                display_method = getattr(self.display, event.name.value)
                display_method(**event.kwargs)
            except Exception as e:
                self.logger.exception(f"`{event.name}` callback failed for {self.display}")
                event.future.set_exception(e)
            else:
                event.future.set_result(None)

    async def run_async(self) -> None:
        """Primary coroutine for all further processing"""
        if self._started:
            raise RuntimeError("Runner has been started more than one time")
        self._started = True
        # Build workflow and display
        workflow: Workflow = self.workflow
        with workflow.configuration.apply():
            display: types.DisplayType = self.display
            display.logger.debug("Starting events processing")
            display_events_flow_processing_task: asyncio.Task = asyncio.create_task(self._process_display_events())
            try:
                await self._send_display_event(
                    DisplayEventName.ON_RUNNER_START,
                    children=workflow.iterate_actions(),
                )
                if C.INTERACTIVE_MODE:
                    await self._send_display_event(DisplayEventName.ON_PLAN_INTERACTION, workflow=workflow)
                await self._run_all_actions()
                await self._send_display_event(DisplayEventName.ON_RUNNER_FINISH)
                if self._execution_failed:
                    raise ExecutionFailed
            finally:
                display_events_flow_processing_task.cancel()

    async def _run_all_actions(self) -> None:
        action_runners: dict[WorkflowActionExecution, asyncio.Task] = {}
        strategy_class: types.StrategyClassType = C.STRATEGY_CLASS
        strategy: types.StrategyType = strategy_class(workflow=self.workflow)
        async for action in strategy:  # type: WorkflowActionExecution
            # Finalize all actions that have been done already
            for maybe_finished_action, corresponding_runner_task in list(action_runners.items()):
                if maybe_finished_action.future.done():
                    self.logger.debug(f"Finalizing done action {maybe_finished_action.name!r} runner")
                    await corresponding_runner_task
                    action_runners.pop(maybe_finished_action)
            self.logger.debug(f"Allocating action runner for {action.name!r}")
            action_runners[action] = asyncio.create_task(self._run_action(action=action))

        # Finalize running actions
        for task in action_runners.values():
            await task

    async def _dispatch_action_messages_to_display(self, action: WorkflowActionExecution) -> None:
        async for event in action.read_messages():
            self._events_flow.put_nowait(event)

    async def _run_action(self, action: WorkflowActionExecution) -> None:
        if not action.enabled:
            action.omit()
            return None
        for dependency in action.ancestors:
            ancestor: WorkflowActionExecution = self.workflow[dependency.name]
            if (
                ancestor.status in (ActionStatus.FAILURE, ActionStatus.SKIPPED, ActionStatus.WARNING)
                and dependency.strict
            ):
                self.logger.debug(f"Action {action} is qualified as skipped due to strict failure: {ancestor}")
                action.skip()
                return None
        self.logger.debug(f"Calling `{DisplayEventName.ON_ACTION_START}` for {action.name!r}")
        await self._send_display_event(DisplayEventName.ON_ACTION_START, source=action)
        self.logger.debug(f"Allocating action dispatcher for {action.name!r}")
        action_messages_reader_task: asyncio.Task = asyncio.create_task(
            self._dispatch_action_messages_to_display(action=action)
        )
        try:
            await action.execute()
        except Exception as e:
            message: str
            if isinstance(e, ActionRunError):
                message = str(e)
            elif isinstance(e, ActionRenderError):
                message = f"Action {action.name!r} rendering failed: {e}"
            else:
                message = f"Action {action.name!r} run exception: {e!r}"
            if message:
                await self._send_display_event(
                    DisplayEventName.ON_ACTION_ERROR,
                    source=action,
                    message=message,
                )
            if action.status == ActionStatus.WARNING:
                self.logger.warning(f"Action {action.name!r} finished with warning status")
            else:
                self.logger.warning(f"Action {action.name!r} execution failed: {e!r}")
                self._execution_failed = True
            self.logger.debug("Action failure traceback", exc_info=True)
        finally:
            await action_messages_reader_task
            self.logger.debug(f"Calling `{DisplayEventName.ON_ACTION_FINISH.value}` for {action.name!r}")
            await self._send_display_event(DisplayEventName.ON_ACTION_FINISH, source=action)

    def run_sync(self):
        """Wrap async run into an event loop"""
        asyncio.run(self.run_async())
