"""Loading dataclasses from dicts"""

import enum
import logging
import pathlib
import typing as t

from .exceptions import RootTypeUnionMatchError
from .loader import DataClassLoader

T = t.TypeVar("T")

__all__ = [
    "from_dict",
    "get_data_class_by_data_signature",
]

logger = logging.getLogger(__name__)


def from_dict(data_type: type[T], data: dict[str, t.Any]) -> T:
    """Create a dataclass instance from dict"""
    class_loader = DataClassLoader(
        validate_types=True,
        cast_types_list=[
            enum.Enum,
            pathlib.Path,
        ],
    )
    return class_loader.from_dict(data_type=data_type, data=data)


def get_data_class_by_data_signature(data_type: type[T], data: dict[str, t.Any]) -> type[T]:
    """Select a dataclass from possible union type"""
    class_loader = DataClassLoader(validate_types=False)
    if not class_loader._is_union(data_type):  # pylint: disable=protected-access
        class_loader.from_dict(data_type=data_type, data=data)
        return data_type

    union_matches: list[type[T]] = []
    inner_types: tuple[type[T], ...] = class_loader._extract_generic_args(data_type)  # pylint: disable=protected-access
    for inner_type in inner_types:
        try:
            source_class = get_data_class_by_data_signature(data_type=inner_type, data=data)
        except Exception as e:
            logger.debug(f"Type {inner_type}: {e}")
        else:
            union_matches.append(source_class)
    if len(union_matches) != 1:
        raise RootTypeUnionMatchError(types=inner_types, keys=sorted(data)) from None
    return union_matches[0]
