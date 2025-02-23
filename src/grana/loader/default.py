"""YAML-based workflow load routines"""

from __future__ import annotations

import typing as t
from functools import lru_cache
from pathlib import Path

import yaml

from .base import AbstractBaseWorkflowLoader
from .utils import DefaultYAMLLoader
from ..actions.base import WorkflowActionExecution, ActionBase
from ..actions.bundled import (
    EchoAction,
    ShellAction,
    SubflowAction,
    DockerShellAction,
)
from ..actions.types import Import
from ..config.constants import C
from ..config.constants.helpers import class_from_module

__all__ = [
    "DefaultYAMLWorkflowLoader",
]


class DefaultYAMLWorkflowLoader(AbstractBaseWorkflowLoader):
    """Default loader for YAML source files"""

    ALLOWED_ROOT_TAGS: set[str] = {"actions", "context", "miscellaneous", "configuration"}

    def get_action_factories_info(self) -> dict[str, tuple[type[ActionBase], str]]:
        return {
            **self._get_static_action_factories_mapping(),
            **self._load_external_action_factories_mapping(),
        }

    @lru_cache(maxsize=1)
    def _get_static_action_factories_mapping(self) -> dict[str, tuple[type[ActionBase], str]]:
        return {
            name: (klass, "built-in")
            for name, klass in (
                ("echo", EchoAction),
                ("shell", ShellAction),
                ("subflow", SubflowAction),
                ("docker-shell", DockerShellAction),
            )
            if klass is not None
        }

    @lru_cache(maxsize=1)
    def _load_external_action_factories_mapping(self) -> dict[str, tuple[type[ActionBase], str]]:
        dynamic_bases_map: dict[str, tuple[type[ActionBase], str]] = {}
        for class_directory in C.ACTION_CLASSES_DIRECTORIES:  # type: str
            class_directory_path = Path(class_directory).resolve()
            if not class_directory_path.exists():
                self.logger.warning(f"Given actions classes directory does not exist: {class_directory_path!r}")
                continue
            if not class_directory_path.is_dir():
                self.logger.warning(f"Given actions classes path is not a directory: {class_directory_path!r}")
                continue
            self.logger.info(f"Loading external action classes from {str(class_directory_path)!r}")
            for class_file in class_directory_path.iterdir():
                if not class_file.is_file() or not class_file.suffix == ".py":
                    continue
                action_type: str = class_file.stem
                self.logger.debug(f"Trying external action class source: {class_file}")
                action_class: type[ActionBase] = t.cast(
                    type[ActionBase],
                    class_from_module(
                        source_path=class_file,
                        class_name="Action",
                        submodule_name=f"actions.{action_type}",
                    ),
                )
                if action_type in dynamic_bases_map:
                    self.logger.warning(f"Class {action_type!r} is already defined: overriding from {class_file}")
                dynamic_bases_map[action_type] = (action_class, str(class_file))
        return dynamic_bases_map

    def _parse_import(self, tag: Import, allowed_root_keys: set[str]) -> None:
        path: str = tag.path
        if not path:
            self._throw(f"Empty import: {path!r}")
        with self._read_file(path) as file_data:
            self._internal_loads_with_filter(
                data=file_data,
                allowed_root_keys=allowed_root_keys,
            )

    def _internal_loads(self, data: t.Union[str, bytes]) -> None:
        self._internal_loads_with_filter(
            data=data,
            allowed_root_keys=self.ALLOWED_ROOT_TAGS,
        )

    def _internal_loads_with_filter(
        self,
        data: t.Union[str, bytes],
        allowed_root_keys: set[str],
    ) -> None:
        if isinstance(data, bytes):
            data = data.decode()
        root_node: dict = yaml.load(data, DefaultYAMLLoader)  # nosec
        if not isinstance(root_node, dict):
            self._throw(f"Unknown workflow structure: {type(root_node)!r} (should be a dict)")
        root_keys: set[str] = set(root_node)
        if not root_keys:
            self._throw(f"Empty root dictionary (expected some of: {', '.join(sorted(self.ALLOWED_ROOT_TAGS))}")
        if unrecognized_keys := root_keys - self.ALLOWED_ROOT_TAGS:
            self._throw(
                f"Unrecognized root keys: {sorted(unrecognized_keys)} "
                f"(expected some of: {', '.join(sorted(self.ALLOWED_ROOT_TAGS))}"
            )
        processable_keys: set[str] = set(root_node) & allowed_root_keys
        if "configuration" in processable_keys:
            self.load_configuration_from_dict(root_node["configuration"])
        with self._loaded_config.apply():
            if "actions" in processable_keys:
                actions: list[dict] = root_node["actions"]
                if not isinstance(actions, list):
                    self._throw(f"'actions' contents should be a list (got {type(actions)!r})")
                for child_node in actions:
                    if isinstance(child_node, dict):
                        action: WorkflowActionExecution = self.build_action_from_dict_data(child_node)
                        self._register_action(action)
                    else:
                        self._throw(f"Unrecognized node type: {type(child_node)!r}")
            if "context" in processable_keys:
                context: t.Union[dict[str, str], list[t.Union[dict[str, str], Import]]] = root_node["context"]
                if isinstance(context, dict):
                    self._loads_contexts_dict(data=context)
                elif isinstance(context, list):
                    for num, item in enumerate(context):
                        if isinstance(item, dict):
                            self._loads_contexts_dict(data=item)
                        elif isinstance(item, Import):
                            self._parse_import(
                                tag=item,
                                allowed_root_keys={"context"},
                            )
                        else:
                            self._throw(f"Context item #{num + 1} is not a dict nor an '!import' (got {type(item)!r})")
                else:
                    self._throw(f"'context' contents should be a dict or a list (got {type(context)!r})")

    def _loads_contexts_dict(self, data: dict[str, t.Any]) -> None:
        for context_key, context_value in data.items():
            if not isinstance(context_key, str):
                self._throw(f"Context keys should be strings (got {type(context_key)!r} for {context_key!r})")
            if context_key in self._gathered_context:
                self.logger.debug(f"Context key redefined: {context_key}")
            else:
                self.logger.debug(f"Context key added: {context_key}")
            self._gathered_context[context_key] = context_value
