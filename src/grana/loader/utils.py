"""Loader utilities"""

from __future__ import annotations

import pathlib

import yaml

from .context import LOADED_FILE_STACK
from ..actions.types import Expression
from ..exceptions import YAMLStructureError
from ..rendering import CommonTemplar

__all__ = [
    "ExpressionYAMLLoader",
    "DefaultYAMLLoader",
]


class ExpressionYAMLLoader(yaml.SafeLoader):
    """Extension parser"""

    @classmethod
    def add_string_constructor(cls, tag: str, target_class: type) -> None:
        """Register simple string constructor with type checking"""

        def construct(_, node):
            if not isinstance(node.value, str):
                raise YAMLStructureError(f"Expected string content after {tag!r}, got {node.value!r}")
            return target_class(node.value)

        cls.add_constructor(tag, construct)


ExpressionYAMLLoader.add_string_constructor("!@", Expression)


class DefaultYAMLLoader(ExpressionYAMLLoader):
    """Parser for default workflow loader"""

    @staticmethod
    def parse_load(loader: DefaultYAMLLoader, data: yaml.ScalarNode):
        """Process `!load` tag in parse-time to load external files"""
        templar: CommonTemplar = LOADED_FILE_STACK.create_associated_templar()
        file_path: pathlib.Path = pathlib.Path(templar.render(data.value))
        with file_path.open("rb") as f, LOADED_FILE_STACK.add(file_path):
            return yaml.load(f, loader.__class__)  # nosec


DefaultYAMLLoader.add_constructor("!load", DefaultYAMLLoader.parse_load)
