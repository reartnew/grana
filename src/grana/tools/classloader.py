"""Loading dataclasses from dicts"""

import dataclasses
import enum
import logging
import pathlib
import typing as t

import dacite
import dacite.core
import dacite.types

T = t.TypeVar("T")

__all__ = [
    "from_dict",
    "get_data_class_by_data_signature",
    "MissingValueError",
    "UnexpectedDataError",
    "WrongTypeError",
    "RootTypeUnionMatchError",
]

MissingValueError = dacite.MissingValueError
UnexpectedDataError = dacite.UnexpectedDataError
WrongTypeError = dacite.WrongTypeError

logger = logging.getLogger(__name__)


class RootTypeUnionMatchError(Exception):
    """Indicates that the union-based argument spec did not match"""

    def __init__(self, types: tuple, keys: list[str]) -> None:
        type_signatures: list[str] = []
        for typ in types:
            type_field_names: list[str] = sorted(f.name for f in dataclasses.fields(typ))
            type_signatures.append(f"{type_field_names} for {typ.__name__}")
        expected_signatures: str = ", ".join(type_signatures)
        super().__init__(f"Got: {keys}, expected one of: {expected_signatures}")


def from_dict(data_class: type[T], data: dict[str, t.Any]) -> T:
    """Use dacite to create a dataclass instance from dict"""
    return dacite.from_dict(
        data_class=data_class,
        data=data,
        config=dacite.Config(
            check_types=True,
            strict=True,
            strict_unions_match=True,
            cast=[
                enum.Enum,
                pathlib.Path,
            ],
        ),
    )


def get_data_class_by_data_signature(data_class: type[T], data: dict[str, t.Any]) -> type[T]:
    """Use dacite to create a dataclass instance from dict"""
    if not dacite.types.is_union(data_class):
        dacite.from_dict(
            data_class=data_class,
            data=data,
            config=dacite.Config(
                check_types=False,
                strict=True,
                strict_unions_match=True,
            ),
        )
        return data_class

    union_matches: list[type[T]] = []
    inner_types: tuple[type[T], ...] = dacite.types.extract_generic(data_class)
    for inner_type in inner_types:
        try:
            get_data_class_by_data_signature(data_class=inner_type, data=data)
            union_matches.append(inner_type)
        except Exception as e:
            logger.debug(f"Type {inner_type}: {e}")
    if len(union_matches) != 1:
        raise RootTypeUnionMatchError(types=inner_types, keys=sorted(data)) from None
    return union_matches[0]
