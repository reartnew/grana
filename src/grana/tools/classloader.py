"""Loading dataclasses from dicts"""

import enum
import pathlib
import typing as t

import dacite

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
            strict_unions_match=False,
            cast=[
                enum.Enum,
                pathlib.Path,
            ],
        )
    return t.cast(
        T,
        dacite.from_dict(
            data_class=data_class,
            data=data,
            config=config,
        ),
    )
