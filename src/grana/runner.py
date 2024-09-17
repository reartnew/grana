"""
Runner has too many dependencies,
thus placed to a separate module.
"""

import asyncio
import functools
import io
import sys
import typing as t
from enum import Enum
from pathlib import Path

import classlogging
import dacite

from . import types
from .actions.base import ActionBase, ArgsBase, ActionStatus
from .config.constants import C
from .display.base import BaseDisplay
from .exceptions import SourceError, ExecutionFailed, ActionRenderError, ActionRunError
from .loader.helpers import get_default_loader_class_for_source
from .rendering import Templar
from .tools.concealment import represent_object_type
from .workflow import Workflow

__all__ = [
    "Runner",
]

IOType = io.TextIOBase
logger = classlogging.get_module_logger()


class Runner(classlogging.LoggerMixin):
    """Main entry object"""

    def __init__(
        self,
        source: t.Union[str, Path, IOType, None] = None,
        display: t.Optional[types.DisplayType] = None,
    ) -> None:
        self._workflow_source: t.Union[Path, IOType] = self._detect_workflow_source(explicit_source=source)
        self._explicit_display: t.Optional[types.DisplayType] = display
        self._started: bool = False
        self._outcomes: t.Dict[str, t.Dict[str, t.Any]] = {}
        self._execution_failed: bool = False

    @functools.cached_property
    def loader(self) -> types.LoaderType:
        """Workflow loader"""
        loader_class: types.LoaderClassType
        if C.WORKFLOW_LOADER_CLASS is not None:
            loader_class = C.WORKFLOW_LOADER_CLASS
        else:
            loader_class = get_default_loader_class_for_source(self._workflow_source)
        self.logger.debug(f"Using workflow loader class: {loader_class}")
        return loader_class()

    @functools.cached_property
    def workflow(self) -> Workflow:
        """Calculated workflow"""
        return (
            self.loader.loads(self._workflow_source.read())
            if isinstance(self._workflow_source, io.TextIOBase)
            else self.loader.load(self._workflow_source)
        )

    @functools.cached_property
    def display(self) -> types.DisplayType:
        """Attached display"""
        if self._explicit_display is not None:
            self.logger.debug(f"Using explicit display: {self._explicit_display}")
            return self._explicit_display
        display_class: types.DisplayClassType = C.DISPLAY_CLASS
        self.logger.debug(f"Using display class: {display_class}")
        return display_class(workflow=self.workflow)

    @functools.cached_property
    def strategy(self) -> types.StrategyType:
        """Strategy iterator"""
        strategy_class: types.StrategyClassType = C.STRATEGY_CLASS
        self.logger.debug(f"Using strategy class: {strategy_class}")
        return strategy_class(workflow=self.workflow)

    @classmethod
    def _detect_workflow_source(cls, explicit_source: t.Union[str, Path, IOType, None] = None) -> t.Union[Path, IOType]:
        if explicit_source is not None:
            if isinstance(explicit_source, IOType):
                return explicit_source
            return Path(explicit_source)
        if C.ACTIONS_SOURCE_FILE is not None:
            source_file: Path = C.ACTIONS_SOURCE_FILE
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

    async def run_async(self) -> None:
        """Primary coroutine for all further processing"""
        # Build workflow and display
        workflow: Workflow = self.workflow
        display: BaseDisplay = self.display
        # Check requirements
        self.loader.check_requirements()
        try:
            display.on_runner_start()
        except Exception:
            self.logger.exception(f"`on_runner_start` callback failed for {display}")
        if C.INTERACTIVE_MODE:
            display.on_plan_interaction(workflow=workflow)
        await self._run_all_actions()
        try:
            display.on_runner_finish()
        except Exception:
            self.logger.exception(f"`on_runner_finish` callback failed for {display}")
        if self._execution_failed:
            raise ExecutionFailed

    async def _run_all_actions(self) -> None:
        if self._started:
            raise RuntimeError("Runner has been started more than one time")
        self._started = True
        action_runners: t.Dict[ActionBase, asyncio.Task] = {}
        # Prefill outcomes map
        for action_name in self.workflow:
            self._outcomes[action_name] = {}
        async for action in self.strategy:  # type: ActionBase
            # Finalize all actions that have been done already
            for maybe_finished_action, corresponding_runner_task in list(action_runners.items()):
                if maybe_finished_action.done():
                    self.logger.trace(f"Finalizing done action {maybe_finished_action.name!r} runner")
                    await corresponding_runner_task
                    action_runners.pop(maybe_finished_action)
            self.logger.trace(f"Allocating action runner for {action.name!r}")
            action_runners[action] = asyncio.create_task(self._run_action(action=action))

        # Finalize running actions
        for task in action_runners.values():
            await task

    @classmethod
    async def _dispatch_action_events_to_display(cls, action: ActionBase, display: BaseDisplay) -> None:
        try:
            async for message in action.read_events():
                display.emit_action_message(source=action, message=message)
        except Exception:
            cls.logger.exception(f"`emit_action_message` failed for {action.name!r}")

    async def _run_action(self, action: ActionBase) -> None:
        if not action.enabled:
            action._internal_omit()  # pylint: disable=protected-access
            return None
        message: str
        try:
            self._render_action(action)
        except Exception as e:
            details: str = str(e) if isinstance(e, ActionRenderError) else repr(e)
            message = f"Action {action.name!r} rendering failed: {details}"
            self.display.emit_action_error(source=action, message=message)
            self.logger.warning(message, exc_info=not isinstance(e, ActionRenderError))
            action._internal_fail(e)  # pylint: disable=protected-access
            self._execution_failed = True
            return
        self.logger.trace(f"Calling `on_action_start` for {action.name!r}")
        try:
            self.display.on_action_start(action)
        except Exception:
            self.logger.exception(f"`on_action_start` callback failed on {action.name!r} for {self.display}")
        self.logger.trace(f"Allocating action dispatcher for {action.name!r}")
        action_events_reader_task: asyncio.Task = asyncio.create_task(
            self._dispatch_action_events_to_display(
                action=action,
                display=self.display,
            )
        )
        try:
            await action
        except Exception as e:
            try:
                self.display.emit_action_error(
                    source=action,
                    message=str(e) if isinstance(e, ActionRunError) else f"Action {action.name!r} run exception: {e!r}",
                )
            except Exception:
                self.logger.exception(f"`emit_action_error` failed for {action.name!r}")
            if action.status == ActionStatus.WARNING:
                self.logger.warning(f"Action {action.name!r} finished with warning status")
            else:
                self.logger.warning(f"Action {action.name!r} execution failed: {e!r}")
                self._execution_failed = True
            self.logger.debug("Action failure traceback", exc_info=True)
        finally:
            self._outcomes[action.name].update(action.get_outcomes())
            await action_events_reader_task
            self.logger.trace(f"Calling `on_action_finish` for {action.name!r}")
            try:
                self.display.on_action_finish(action)
            except Exception:
                self.logger.exception(f"`on_action_finish` callback failed on {action.name!r} for {self.display}")

    def run_sync(self):
        """Wrap async run into an event loop"""
        asyncio.run(self.run_async())

    def _render_action(self, action: ActionBase) -> None:
        """Prepare action to execution by rendering its template fields"""
        templar: Templar = Templar(
            outcomes_map=self._outcomes,
            action_states={name: self.workflow[name].status.value for name in self.workflow},
            context_map=self.workflow.context,
        )

        rendered_args_dict: dict = templar.recursive_render(self.loader.get_original_args_dict_for_action(action))
        try:
            parsed_args: ArgsBase = dacite.from_dict(
                data_class=type(action.args),
                data=rendered_args_dict,
                config=dacite.Config(
                    strict=True,
                    cast=[Enum, Path],
                ),
            )
        except dacite.WrongTypeError as e:
            raise ActionRenderError(
                f"Unrecognized {e.field_path!r} content type: {represent_object_type(e.value)}"
                f" (expected {e.field_type!r})"
            ) from None
        action.args = parsed_args
