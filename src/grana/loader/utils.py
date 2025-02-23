"""Loader utilities"""

from __future__ import annotations

import yaml

from ..actions.types import Expression
from ..exceptions import YAMLStructureError

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
