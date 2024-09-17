"""Runtime values concealment helpers."""

import typing as t

__all__ = [
    "represent_object_type",
]


def represent_object_type(obj: t.Any) -> str:
    """Build a string representation of an object type to disguise real values"""
    if isinstance(obj, t.Mapping):
        if not obj:
            return "typing.Dict"
        return f"typing.Dict[{_represent_collection_as_union(obj)}, {_represent_collection_as_union(obj.values())}]"
    if isinstance(obj, t.List):
        if not obj:
            return "typing.List"
        return f"typing.List[{_represent_collection_as_union(obj)}]"
    return obj.__class__.__name__


def _represent_collection_as_union(collection: t.Iterable) -> str:
    sorted_unique_types_names: t.List[str] = sorted({represent_object_type(item) for item in collection})
    if len(sorted_unique_types_names) == 1:
        return sorted_unique_types_names[0]
    none_type_name: str = type(None).__name__
    if len(sorted_unique_types_names) == 2 and none_type_name in sorted_unique_types_names:
        non_none_types = [v for v in sorted_unique_types_names if v != none_type_name]
        return f"typing.Optional[{non_none_types[0]}]"
    return f"typing.Union[{', '.join(sorted_unique_types_names)}]"
