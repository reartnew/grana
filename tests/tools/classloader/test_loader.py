"""Various tests for class loader"""

import dataclasses
import typing as t

from pytest_data_suites import DataSuite

from grana.tools.classloader.loader import DataClassLoader


@dataclasses.dataclass
class GenericUnion:
    """Universal union"""

    foo: t.Union[str, float]


try:
    from .syntax_specific import SimplifiedUnion
except (SyntaxError, TypeError):
    SimplifiedUnion = GenericUnion  # type: ignore[assignment, misc]


class LoadCase(t.TypedDict):
    """Class loading case definition"""

    data_type: type
    data: dict


class LoadSuite(DataSuite):
    """Loading suite"""

    generic_union_str = LoadCase(data_type=GenericUnion, data={"foo": "bar"})
    generic_union_float = LoadCase(data_type=GenericUnion, data={"foo": 1})
    simplified_union_str = LoadCase(data_type=SimplifiedUnion, data={"foo": "bar"})
    simplified_union_float = LoadCase(data_type=SimplifiedUnion, data={"foo": 1})


@LoadSuite.parametrize
def test_load(data_type: type, data: dict):
    """Try loading"""
    assert DataClassLoader().from_dict(data_type=data_type, data=data)
