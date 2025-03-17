"""Dataclass loading exceptions"""

import dataclasses
import typing as t

from ..concealment import represent_object_type


class ClassLoaderError(Exception):
    """Base load error"""

    def __init__(self, path: str, message: str) -> None:
        self.path: str = path or "/"
        self.message: str = message
        info: str = self.path if self.message is None else f"{self.message} (at {self.path!r})"
        super().__init__(info)


class TypeMatchError(ClassLoaderError):
    """Type mismatches"""

    def __init__(self, data_type: type, value: t.Any, path: str) -> None:
        value_type_str: str = represent_object_type(value)
        message: str = f"Unrecognized content type: {value_type_str} (expected {data_type!r})"
        super().__init__(path=path, message=message)


class MissingValueError(ClassLoaderError):
    """Missing value for field"""

    def __init__(self, path: str) -> None:
        message: str = "Missing value for field"
        super().__init__(path=path, message=message)


class UnionTypeMatchError(TypeMatchError):
    """None of the union types match"""


class StrictUnionTypeMatchError(ClassLoaderError):
    """More than one of the union types match"""

    def __init__(self, matches: dict[type, t.Any], path: str) -> None:
        match_types = ", ".join(sorted(str(data_type) for data_type in matches))
        message: str = f"Multiple union matches found: {match_types}"
        super().__init__(path=path, message=message)


class UnexpectedDataError(ClassLoaderError):
    """Unexpected fields"""

    def __init__(self, keys: set[str], path: str) -> None:
        message: str = f"Unrecognized fields: {', '.join(repr(k) for k in sorted(keys))}"
        super().__init__(path=path, message=message)


class RootTypeUnionMatchError(ClassLoaderError):
    """Indicates that the union-based argument spec did not match"""

    def __init__(self, types: tuple, keys: list[str]) -> None:
        type_signatures: list[str] = []
        for typ in types:
            type_field_names: list[str] = sorted(f.name for f in dataclasses.fields(typ))
            type_signatures.append(f"{type_field_names} for {typ.__name__}")
        expected: str = ", ".join(type_signatures)
        message: str = f"Data did not conform to allowed type signatures: {keys}, expected one of: {expected}"
        super().__init__(path="", message=message)
