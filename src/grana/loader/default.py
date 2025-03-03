"""YAML-based workflow load routines"""

from __future__ import annotations

import functools
import typing as t
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
from ..config.constants import C
from ..config.constants.cache import CACHE
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

    @CACHE.wrap
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

    @CACHE.wrap
    def _load_external_action_factories_mapping(self) -> dict[str, tuple[type[ActionBase], str]]:
        return self._get_action_factories_from_sources_tuple(sources=tuple(C.ACTION_CLASSES_DIRECTORIES))

    @classmethod
    @functools.lru_cache(1)
    def _get_action_factories_from_sources_tuple(cls, sources: tuple[Path]) -> dict[str, tuple[type[ActionBase], str]]:
        dynamic_bases_map: dict[str, tuple[type[ActionBase], str]] = {}
        for class_directory_path in sources:  # type: Path
            class_directory_path = class_directory_path.resolve()
            if not class_directory_path.exists():
                cls.logger.warning(f"Given actions classes directory does not exist: {class_directory_path!r}")
                continue
            if not class_directory_path.is_dir():
                cls.logger.warning(f"Given actions classes path is not a directory: {class_directory_path!r}")
                continue
            cls.logger.info(f"Loading external action classes from {str(class_directory_path)!r}")
            for class_file in class_directory_path.iterdir():
                if not class_file.is_file() or not class_file.suffix == ".py":
                    continue
                action_type: str = class_file.stem
                cls.logger.debug(f"Trying external action class source: {class_file}")
                action_class: type[ActionBase] = t.cast(
                    type[ActionBase],
                    class_from_module(
                        source_path=class_file,
                        class_name="Action",
                        submodule_name=f"actions.{action_type}",
                    ),
                )
                if action_type in dynamic_bases_map:
                    cls.logger.warning(f"Class {action_type!r} is already defined: overriding from {class_file}")
                dynamic_bases_map[action_type] = (action_class, str(class_file))
        return dynamic_bases_map

    def _internal_load_from_text(self, data: str) -> None:
        root_node: dict = yaml.load(data, DefaultYAMLLoader)  # nosec
        if not isinstance(root_node, dict):
            self._throw(f"Unknown workflow structure: {type(root_node)!r} (should be a dict)")
        self._internal_load_from_dict(data=root_node)

    def _internal_load_from_dict(self, data: dict) -> None:
        root_keys: set[str] = set(data)
        if not root_keys:
            self._throw(f"Empty root dictionary (expected some of: {', '.join(sorted(self.ALLOWED_ROOT_TAGS))}")
        if unrecognized_keys := root_keys - self.ALLOWED_ROOT_TAGS:
            self._throw(
                f"Unrecognized root keys: {sorted(unrecognized_keys)} "
                f"(expected some of: {', '.join(sorted(self.ALLOWED_ROOT_TAGS))}"
            )
        processable_keys: set[str] = set(data) & self.ALLOWED_ROOT_TAGS
        if "configuration" in processable_keys:
            self.load_configuration_from_dict(data["configuration"])
        with self._loaded_config.apply():
            if "actions" in processable_keys:
                actions: list[dict] = data["actions"]
                if not isinstance(actions, list):
                    self._throw(f"'actions' contents should be a list (got {type(actions)!r})")
                for child_node in actions:
                    if not isinstance(child_node, dict):
                        self._throw(f"Unrecognized node type: {type(child_node)!r}")
                    action: WorkflowActionExecution = self.build_action_from_dict_data(child_node)
                    self._register_action(action)
            if "context" in processable_keys:
                context: dict[str, t.Any] = data["context"]
                if not isinstance(context, dict):
                    self._throw(f"'context' contents should be a dict (got {type(context)!r})")
                self._loads_contexts_dict(data=context)

    def _loads_contexts_dict(self, data: dict[str, t.Any]) -> None:
        for context_key, context_value in data.items():
            if not isinstance(context_key, str):
                self._throw(f"Context keys should be strings (got {type(context_key)!r} for {context_key!r})")
            self.logger.debug(f"Context key defined: {context_key}")
            self._gathered_context[context_key] = context_value
