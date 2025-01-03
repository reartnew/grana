"""Display utilities tests"""

import typing as t

from pytest_data_suites import DataSuite

from grana.display.utils import Tree, locate_parent_name_by_prefix


def test_tree_representation() -> None:
    """Generic tree representation"""
    tree: Tree[str] = Tree()

    def _put_payload(prefix: str, count: int, parent_name: t.Optional[str] = None) -> None:
        tree.put(((f"{prefix}-{num}", f"{prefix}-{num}") for num in range(count)), parent_name=parent_name)

    _put_payload("foo", 3)
    _put_payload("bar", 4, parent_name="foo-1")
    _put_payload("baz", 1, parent_name="bar-0")
    _put_payload("qux", 2, parent_name="baz-0")
    output = [f"{pref}{obj}" for pref, obj in tree.generate_ascii_representation()]
    assert output == [
        "foo-0",
        "foo-1",
        "├──bar-0",
        "│  └──baz-0",
        "│     ├──qux-0",
        "│     └──qux-1",
        "├──bar-1",
        "├──bar-2",
        "└──bar-3",
        "foo-2",
    ]


class LocateParentTestData(t.TypedDict):
    """Arguments for testing locate_parent_name_by_prefix"""

    children: t.List[str]
    candidates: t.List[str]
    result: str


class LocateParentTestDataSuite(DataSuite):
    """Argument sets for testing locate_parent_name_by_prefix"""

    simple_check = LocateParentTestData(
        children=["fo/bar", "fo/baz"],
        candidates=["f", "fo", "foo"],
        result="fo",
    )
    shorter_candidate_with_same_prefix = LocateParentTestData(
        children=["foo/bar", "foo/baz"],
        candidates=["foobar", "foo"],
        result="foo",
    )


@LocateParentTestDataSuite.parametrize
def test_locate_parent_name_by_prefix(children: t.List[str], candidates: t.List[str], result: str) -> None:
    """Test locate_parent_name_by_prefix call"""
    assert locate_parent_name_by_prefix(children=children, candidates=candidates) == result
