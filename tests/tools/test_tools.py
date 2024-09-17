"""Runtime values concealment tests"""

import typing as t

from pytest_data_suites import DataSuite

from grana.tools.concealment import represent_object_type


class RepresentTestCase(t.TypedDict):
    """Concealed representation test case variables"""

    obj: t.Any
    representation: str


class RepresentDataSuite(DataSuite):
    """Concealed representation test cases"""

    none = RepresentTestCase(obj=None, representation="NoneType")
    empty_list = RepresentTestCase(obj=[], representation="typing.List")
    empty_dict = RepresentTestCase(obj={}, representation="typing.Dict")
    simple_list = RepresentTestCase(obj=["a"], representation="typing.List[str]")
    simple_dict = RepresentTestCase(obj={"a": "b"}, representation="typing.Dict[str, str]")
    optional_first = RepresentTestCase(obj=[None, "a"], representation="typing.List[typing.Optional[str]]")
    optional_last = RepresentTestCase(obj=["a", None], representation="typing.List[typing.Optional[str]]")
    nested_dict = RepresentTestCase(obj={"a": {"b": "c"}}, representation="typing.Dict[str, typing.Dict[str, str]]")
    complex_union = RepresentTestCase(
        obj={"a": 1, "b": None, 2: ["c", 1.0]},
        representation="typing.Dict[typing.Union[int, str], "
        "typing.Union[NoneType, int, typing.List[typing.Union[float, str]]]]",
    )


@RepresentDataSuite.parametrize
def test_represent_object_type(obj: t.Any, representation: str) -> None:
    """Check multiple representation cases"""
    assert represent_object_type(obj) == representation
