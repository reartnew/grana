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
            type_signatures.append(str(sorted(f.name for f in dataclasses.fields(typ))))
        expected_signatures: str = ", ".join(type_signatures)
        super().__init__(f"Got: {keys}, expected one of: {expected_signatures}")


def from_dict(data_class: type[T], data: dict[str, t.Any], dry_run: bool = False) -> T:
    """Use dacite to create a dataclass instance from dict"""
    config: dacite.Config
    if dry_run:
        config = dacite.Config(
            check_types=False,
            strict=True,
            strict_unions_match=True,
        )
    else:
        config = dacite.Config(
            check_types=True,
            strict=True,
            strict_unions_match=True,
            cast=[
                enum.Enum,
                pathlib.Path,
            ],
        )
    if not dacite.types.is_union(data_class):
        return dacite.from_dict(
            data_class=data_class,
            data=data,
            config=config,
        )

    union_matches: dict[type, T] = {}
    for inner_type in dacite.types.extract_generic(data_class):
        try:
            value = dacite.from_dict(data_class=inner_type, data=data, config=config)
            if dacite.types.is_instance(value, inner_type):
                union_matches[inner_type] = value
        except Exception as e:
            logger.debug(e)
    if len(union_matches) != 1:
        raise RootTypeUnionMatchError(
            types=dacite.types.extract_generic(data_class),
            keys=sorted(data),
        ) from None
    return union_matches.popitem()[1]
