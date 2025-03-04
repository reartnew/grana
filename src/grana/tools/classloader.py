"""Loading dataclasses from dicts"""

import enum
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
]

MissingValueError = dacite.MissingValueError
UnexpectedDataError = dacite.UnexpectedDataError
WrongTypeError = dacite.WrongTypeError


def from_dict(data_class: type[T], data: dict, dry_run: bool = False) -> T:
    """Use dacite to create a dataclass instance from dict"""
    config: dacite.Config
    if dry_run:
        config = dacite.Config(
            check_types=False,
            strict=True,
            strict_unions_match=False,
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
        return t.cast(
            T,
            dacite.from_dict(
                data_class=data_class,
                data=data,
                config=config,
            ),
        )
    # pylint: disable=protected-access
    return t.cast(
        T,
        dacite.core._build_value_for_union(
            union=data_class,
            data=data,
            config=config,
        ),
    )
