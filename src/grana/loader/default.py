"""YAML-based workflow load routines"""

from __future__ import annotations

import typing as t
from functools import lru_cache
from pathlib import Path

import yaml

from .base import AbstractBaseWorkflowLoader
from ..actions.base import ActionBase
from ..actions.bundled import (
    EchoAction,
    ShellAction,
    DockerShellAction,
)
from ..actions.types import ObjectTemplate, Import
from ..config.constants import C
from ..config.constants.helpers import maybe_class_from_module
from ..exceptions import YAMLStructureError

__all__ = [
    "DefaultYAMLWorkflowLoader",
]


class YAMLLoader(yaml.SafeLoader):
    """Extension loader"""

    @classmethod
    def add_string_constructor(cls, tag: str, target_class: type) -> None:
        """Register simple string constructor with type checking"""

        def construct(_, node):
            if not isinstance(node.value, str):
                raise YAMLStructureError(f"Expected string content after {tag!r}, got {node.value!r}")
            return target_class(node.value)

        cls.add_constructor(tag, construct)


YAMLLoader.add_string_constructor("!@", ObjectTemplate)
YAMLLoader.add_string_constructor("!import", Import)


class DefaultYAMLWorkflowLoader(AbstractBaseWorkflowLoader):
    """Default loader for YAML source files"""

    ALLOWED_ROOT_TAGS: t.Set[str] = {"actions", "context", "miscellaneous", "configuration"}
    STATIC_ACTION_FACTORIES = {
        name: klass
        for name, klass in (
            ("echo", EchoAction),
            ("shell", ShellAction),
            ("docker-shell", DockerShellAction),
        )
        if klass is not None
    }

    def _get_action_factory_by_type(self, action_type: str) -> t.Type[ActionBase]:
        if (dynamically_resolved_action_class := self._load_external_action_factories().get(action_type)) is not None:
            return dynamically_resolved_action_class
        return super()._get_action_factory_by_type(action_type)

    @lru_cache(maxsize=1)
    def _load_external_action_factories(self) -> t.Dict[str, t.Type[ActionBase]]:
        dynamic_bases_map: t.Dict[str, t.Type[ActionBase]] = {}
        for class_directory in C.ACTION_CLASSES_DIRECTORIES:  # type: str
            class_directory_path = Path(class_directory).resolve()
            self.logger.info(f"Loading external action classes from {str(class_directory_path)!r}")
            for class_file in class_directory_path.iterdir():
                if not class_file.is_file() or not class_file.suffix == ".py":
                    continue
                action_type: str = class_file.stem
                self.logger.debug(f"Trying external action class source: {class_file}")
                action_class: t.Type[ActionBase] = t.cast(
                    t.Type[ActionBase],
                    maybe_class_from_module(
                        path_str=str(class_file),
                        class_name="Action",
                        submodule_name=f"actions.{action_type}",
                    ),
                )
                if action_type in dynamic_bases_map:
                    self.logger.warning(f"Class {action_type!r} is already defined: overriding from {class_file}")
                dynamic_bases_map[action_type] = action_class
        return dynamic_bases_map

    def _parse_import(self, tag: Import, allowed_root_keys: t.Set[str]) -> None:
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
        allowed_root_keys: t.Set[str],
    ) -> None:
        if isinstance(data, bytes):
            data = data.decode()
        root_node: dict = yaml.load(data, YAMLLoader)  # nosec
        if not isinstance(root_node, dict):
            self._throw(f"Unknown workflow structure: {type(root_node)!r} (should be a dict)")
        root_keys: t.Set[str] = set(root_node)
        if not root_keys:
            self._throw(f"Empty root dictionary (expected some of: {', '.join(sorted(self.ALLOWED_ROOT_TAGS))}")
        if unrecognized_keys := root_keys - self.ALLOWED_ROOT_TAGS:
            self._throw(
                f"Unrecognized root keys: {sorted(unrecognized_keys)} "
                f"(expected some of: {', '.join(sorted(self.ALLOWED_ROOT_TAGS))}"
            )
        processable_keys: t.Set[str] = set(root_node) & allowed_root_keys
        if "actions" in processable_keys:
            actions: t.List[t.Union[dict, Import]] = root_node["actions"]
            if not isinstance(actions, list):
                self._throw(f"'actions' contents should be a list (got {type(actions)!r})")
            for child_node in actions:
                if isinstance(child_node, dict):
                    action: ActionBase = self.build_action_from_dict_data(child_node)
                    self._register_action(action)
                elif isinstance(child_node, Import):
                    self._parse_import(
                        tag=child_node,
                        allowed_root_keys={"actions"},
                    )
                else:
                    self._throw(f"Unrecognized node type: {type(child_node)!r}")
        if "context" in processable_keys:
            context: t.Union[t.Dict[str, str], t.List[t.Union[t.Dict[str, str], Import]]] = root_node["context"]
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
        if "configuration" in processable_keys:
            self.load_configuration_from_dict(root_node["configuration"])

    def _loads_contexts_dict(self, data: t.Dict[str, t.Any]) -> None:
        for context_key, context_value in data.items():
            if not isinstance(context_key, str):
                self._throw(f"Context keys should be strings (got {type(context_key)!r} for {context_key!r})")
            if context_key in self._gathered_context:
                self.logger.debug(f"Context key redefined: {context_key}")
            else:
                self.logger.debug(f"Context key added: {context_key}")
            self._gathered_context[context_key] = context_value
