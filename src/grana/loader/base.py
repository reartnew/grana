"""Base interface class for all loaders"""

from __future__ import annotations

import collections
import contextlib
import dataclasses
import typing as t
from pathlib import Path

from .context import LOADED_FILE_STACK
from ..actions.base import WorkflowActionExecution, ActionBase, ActionDependency, ActionSeverity
from ..actions.constants import ACTION_RESERVED_FIELD_NAMES
from ..config.constants.workflow import WorkflowConfiguration
from ..exceptions import LoadError, ActionArgumentsLoadError
from ..logging import WithLogger
from ..rendering import WorkflowTemplar, CommonTemplar
from ..tools.classloader import from_dict
from ..workflow import Workflow

__all__ = [
    "AbstractBaseWorkflowLoader",
]


class AbstractBaseWorkflowLoader(WithLogger):
    """Loaders base class"""

    def __init__(self) -> None:
        self._executions: dict[str, WorkflowActionExecution] = {}
        self._gathered_context: dict[str, t.Any] = {}
        self._action_type_counters: dict[str, int] = collections.defaultdict(int)
        self._loaded_workflow: t.Optional[Workflow] = None
        self._loaded_config: WorkflowConfiguration = WorkflowConfiguration()

    @property
    def workflow(self) -> Workflow:
        """Loaded workflow getter"""
        # Check for typing and just in case
        if self._loaded_workflow is None:
            raise RuntimeError("No workflow was loaded")  # pragma: no cover
        return self._loaded_workflow

    @workflow.setter
    def workflow(self, workflow: Workflow) -> None:
        """Loaded workflow setter"""
        # Check for typing and just in case
        if self._loaded_workflow is not None:
            raise RuntimeError("Workflow was loaded already")  # pragma: no cover
        self._loaded_workflow = workflow

    def _register_action(self, action_execution: WorkflowActionExecution) -> None:
        if action_execution.name in self._executions:
            self._throw(f"Action declared twice: {action_execution.name!r}")
        self._executions[action_execution.name] = action_execution

    def _throw(self, message: str) -> t.NoReturn:
        """Raise loader exception from text"""
        raise LoadError(message=message, stack=LOADED_FILE_STACK.get_all()) from None

    def _internal_load_from_file(self, source_file: Path) -> None:
        """Load workflow partially from file (can be called recursively).
        :param source_file: either Path or string object pointing at a file"""
        with self._read_file(source_file) as file_data:
            self._internal_load_from_text(file_data)

    @contextlib.contextmanager
    def _read_file(self, source_file: Path) -> t.Iterator[str]:
        """Read file data"""
        source_resolved_file_path: Path = source_file.resolve()
        with LOADED_FILE_STACK.add(source_resolved_file_path):
            self.logger.debug(f"Loading workflow file: {source_resolved_file_path}")
            if not source_resolved_file_path.is_file():
                self._throw(f"Workflow file not found: {source_resolved_file_path}")
            yield source_resolved_file_path.read_text(encoding="utf-8")

    def _internal_load_from_text(self, data: str) -> None:
        """Load workflow partially from text (can be called recursively)"""
        raise NotImplementedError

    def _internal_load_from_dict(self, data: dict) -> None:
        """Load workflow partially from a dictionary (can be called recursively)"""
        raise NotImplementedError

    def get_action_factories_info(self) -> dict[str, tuple[type[ActionBase], str]]:
        """Returns a mapping of action factories names to its implementation classes and source information"""
        raise NotImplementedError

    def _get_action_factory_by_type(self, action_type: str) -> type[ActionBase]:
        action_info: t.Optional[tuple[type[ActionBase], str]] = self.get_action_factories_info().get(action_type)
        if action_info is None:
            self._throw(f"Unknown action type: {action_type}")
        return action_info[0]

    def load_from_text(self, data: str) -> Workflow:
        """Load workflow from text"""
        self._internal_load_from_text(data=data)
        self.workflow = Workflow(
            self._executions,
            context=self._gathered_context,
            configuration=self._loaded_config,
        )
        return self.workflow

    def load_from_file(self, source_file: Path) -> Workflow:
        """Load workflow from file"""
        self._internal_load_from_file(source_file=source_file)
        self.workflow = Workflow(
            self._executions,
            context=self._gathered_context,
            source_file=Path(source_file),
            configuration=self._loaded_config,
        )
        return self.workflow

    def load_from_dict(self, data: dict) -> Workflow:
        """Load workflow from file"""
        self._internal_load_from_dict(data=data)
        self.workflow = Workflow(
            self._executions,
            context=self._gathered_context,
            configuration=self._loaded_config,
        )
        return self.workflow

    def build_dependency_from_node(self, dep_node: t.Union[str, dict]) -> ActionDependency:
        """Unified method to process transform dependency source data"""
        if isinstance(dep_node, str):
            return ActionDependency(name=dep_node)
        if not isinstance(dep_node, dict):
            self._throw(f"Unrecognized dependency node structure: {type(dep_node)!r} (expected a string or a dict)")
        unexpected_dep_keys: set[str] = set(dep_node) - {"name", "strict", "external"}
        if unexpected_dep_keys:
            self._throw(f"Unrecognized dependency node keys: {sorted(unexpected_dep_keys)}")
        # Dependency name
        if "name" not in dep_node:
            self._throw(f"Name not specified for the dependency: {sorted(dep_node.items())}")
        dep_name: str = dep_node["name"]
        if not isinstance(dep_name, str):
            self._throw(f"Unrecognized dependency name type: {type(dep_name)!r} (expected a string)")
        if not dep_name:
            self._throw("Empty dependency name met")
        # Dependency 'strict' attr
        if "strict" not in dep_node:
            return ActionDependency(name=dep_name)
        strict: bool = dep_node["strict"]
        if not isinstance(strict, bool):
            self._throw(f"Unrecognized 'strict' attribute type: {type(strict)!r} (expected boolean)")
        return ActionDependency(name=dep_name, strict=strict)

    def build_action_from_dict_data(self, node: dict[str, t.Any]) -> WorkflowActionExecution:
        """Process a dictionary representing an action"""
        # Split node data into service fields and args
        service_fields: dict[str, t.Any] = {}
        raw_args: dict[str, t.Any] = {}
        for key, value in node.items():
            if key in ACTION_RESERVED_FIELD_NAMES:
                service_fields[key] = value
            else:
                raw_args[key] = value
        # Action type
        if "type" not in service_fields:
            self._throw("'type' not specified for action")
        action_type: str = service_fields["type"]
        action_class: type[ActionBase] = self._get_action_factory_by_type(action_type)
        # Action name
        name: str
        if "name" in service_fields:
            name = service_fields["name"]
            if not isinstance(name, str):
                self._throw(f"Unexpected name type: {type(name)!r} (should be a string")
            if not name:
                self._throw("Action node name is empty")
        else:
            if (action_counter := self._action_type_counters[action_type]) > 0:
                auto_name_suffix: str = f"-{action_counter + 1}"
            else:
                auto_name_suffix = ""
            name = f"{action_type}{auto_name_suffix}"
        self._action_type_counters[action_type] += 1
        # Description
        description: t.Optional[str] = service_fields.get("description", None)
        if description is not None and not isinstance(description, str):
            self._throw(f"Unrecognized 'description' content type: {type(description)!r} (expected optional string)")
        # Dependencies
        deps_node: t.Union[str, list[t.Union[str, dict]]] = service_fields.get("expects", [])
        if not isinstance(deps_node, str) and not isinstance(deps_node, list):
            self._throw(f"Unrecognized 'expects' content type: {type(deps_node)!r} (expected a string or list)")
        if isinstance(deps_node, str):
            deps_node = [deps_node]
        dependencies: list[ActionDependency] = [self.build_dependency_from_node(dep_node) for dep_node in deps_node]
        # Selectable
        selectable: bool = service_fields.get("selectable", True)
        if not isinstance(selectable, bool):
            self._throw(f"Unrecognized 'selectable' content type: {type(selectable)!r} (expected a bool)")
        # Severity
        severity_str: str = service_fields.get("severity", ActionSeverity.NORMAL.value)
        if not isinstance(severity_str, str):
            self._throw(f"Unrecognized 'severity' content type: {type(severity_str)!r} (expected a string)")
        try:
            severity = ActionSeverity(severity_str)
        except ValueError:
            valid_severities: str = ", ".join(sorted(s.value for s in ActionSeverity))
            self._throw(f"Invalid severity: {severity_str!r} (expected one of: {valid_severities})")
        locals_map: dict[str, t.Any] = service_fields.get("locals", {})
        if not isinstance(locals_map, dict):
            self._throw(f"'locals' contents should be a dict (got {type(locals_map)!r})")
        for local_key in locals_map:
            if not isinstance(local_key, str):
                self._throw(f"'locals' keys should be strings (got {type(local_key)!r} for {local_key!r})")
        try:
            action_instance: WorkflowActionExecution = WorkflowActionExecution(
                name=name,
                action_class=action_class,
                raw_args=raw_args,
                description=description,
                ancestors=dependencies,
                selectable=selectable,
                severity=severity,
                locals_map=locals_map,
                templar_factory=self._get_workflow_templar,
            )
        except ActionArgumentsLoadError as e:
            self._throw(str(e))
        return action_instance

    def load_configuration_from_dict(self, configuration_dict: dict[str, t.Any]) -> None:
        """Process configuration dictionary"""
        if not isinstance(configuration_dict, dict):
            self._throw(f"'configuration' contents should be a dict (got {type(configuration_dict)!r})")
        allowed_cfg_keys: set[str] = {field.name for field in dataclasses.fields(WorkflowConfiguration)}
        for unrecognized_cfg_key in sorted(set(configuration_dict) - allowed_cfg_keys):
            self.logger.warning(f"Unrecognized configuration key: {unrecognized_cfg_key!r}")
            configuration_dict.pop(unrecognized_cfg_key)
        templar: CommonTemplar = LOADED_FILE_STACK.create_associated_templar()
        rendered_configuration_dict: dict[str, t.Any] = templar.render(configuration_dict)
        self._loaded_config = from_dict(data_type=WorkflowConfiguration, data=rendered_configuration_dict)

    def _get_workflow_templar(self, locals_map: dict) -> WorkflowTemplar:
        return self.workflow.get_templar(locals_map)
