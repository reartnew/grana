"""Common loader utilities"""

from __future__ import annotations

import sys
import types
import typing as t

__all__ = [
    "get_class_annotations",
]

OptionalDict = t.Optional[t.Dict[str, t.Any]]


def get_class_annotations(obj: t.Any) -> t.Dict[str, t.Any]:
    """Different pythons hold __annotations__ attribute values as strings or real types, depending on the version."""
    # Resolve class first
    class_definition: type = obj if isinstance(obj, type) else obj.__class__
    class_dict: OptionalDict = getattr(class_definition, "__dict__", None)
    annotations_source: OptionalDict = None
    if class_dict is not None and hasattr(class_dict, "get"):
        annotations_source = class_dict.get("__annotations__", None)
        if isinstance(annotations_source, types.GetSetDescriptorType):
            annotations_source = None  # pragma: no cover

    class_globals: OptionalDict = None
    module_name: t.Optional[str] = getattr(class_definition, "__module__", None)
    if module_name:
        module: t.Optional[types.ModuleType] = sys.modules.get(module_name, None)
        if module:
            class_globals = getattr(module, "__dict__", None)
    class_locals = dict(vars(class_definition))

    if annotations_source is None:
        return {}

    if not isinstance(annotations_source, dict):
        raise ValueError(f"{class_definition!r}.__annotations__ is neither a dict nor None")  # pragma: no cover

    # Unwrap class
    while True:
        if hasattr(class_definition, "__wrapped__"):  # pragma: no cover
            class_definition = class_definition.__wrapped__
            continue
        break
    if hasattr(class_definition, "__globals__"):
        class_globals = class_definition.__globals__  # pragma: no cover

    # Eval finally
    return {
        # pylint: disable=eval-used
        key: value if not isinstance(value, str) else eval(value, class_globals, class_locals)  # nosec
        for key, value in annotations_source.items()
    }
