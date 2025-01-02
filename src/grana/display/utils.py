"""Display utility functions."""

import dataclasses
import itertools
import typing as t

__all__ = [
    "AsciiTree",
    "locate_insert_position_py_prefix",
]

T = t.TypeVar("T")
TopologyGeneratorType = t.Generator[t.Tuple[T, str], None, None]


@dataclasses.dataclass
class Node(t.Generic[T]):
    """Topology relations representation"""

    content: T
    children: list


class AsciiTree(t.Generic[T]):
    """ASCII tree generic builder"""

    def __init__(self):
        self._root_nodes_list: list[Node[T]] = []
        self._nodes_map: dict[str, Node[T]] = {}

    def put(
        self,
        *,
        items: t.Iterable[T],
        names: t.Callable[[T], str],
        parent_name: t.Optional[str] = None,
    ) -> None:
        """Put items into the topology"""
        nodes_list: t.List[Node[T]] = []
        for item in items:
            node: Node[T] = Node(content=item, children=[])
            nodes_list.append(node)
            name: str = names(item)
            self._nodes_map[name] = node
        if parent_name is None:
            self._root_nodes_list = nodes_list
        else:
            self._nodes_map[parent_name].children = nodes_list

    def generate_status_tree_components(self) -> TopologyGeneratorType:
        """Generate status tree components"""
        yield from self._internal_tree_generate(nodes=self._root_nodes_list, prefix=None)

    def _internal_tree_generate(self, nodes: t.List[Node[T]], prefix: t.Optional[str]) -> TopologyGeneratorType:
        last_node_num: int = len(nodes) - 1
        for num, node in enumerate(nodes):
            is_last_node: bool = num == last_node_num
            if prefix is None:
                yield node.content, ""
                yield from self._internal_tree_generate(
                    nodes=node.children,
                    prefix="",
                )
            else:
                yield node.content, prefix + ("└──" if is_last_node else "├──")
                yield from self._internal_tree_generate(
                    nodes=node.children,
                    prefix=prefix + ("   " if is_last_node else "│  "),
                )


def _get_common_prefix(*strings: str) -> str:
    character_tuples: t.Iterable[t.Tuple[str, ...]] = zip(*strings)
    common_prefix_iterator = itertools.takewhile(lambda chars: all(chars[0] == c for c in chars), character_tuples)
    return "".join(common_chars[0] for common_chars in common_prefix_iterator)


def locate_insert_position_py_prefix(source: t.Iterable[str], receiver: t.Iterable[str]) -> t.Tuple[int, int]:
    """Define the proper position to insert data into the existing source"""
    slice_position: int = -1
    longest_match_length: int = -1
    sources_common_prefix: str = _get_common_prefix(*source)
    for receiver_position, receiver_item in enumerate(receiver):
        match_length = len(_get_common_prefix(receiver_item, sources_common_prefix))
        if match_length > longest_match_length:
            longest_match_length = match_length
            slice_position = receiver_position
    return slice_position, longest_match_length
