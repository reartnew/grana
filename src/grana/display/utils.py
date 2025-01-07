"""Display utility functions."""

import dataclasses
import itertools
import typing as t

__all__ = [
    "Tree",
    "locate_parent_name_by_prefix",
]

T = t.TypeVar("T")
AsciiLinesGeneratorType = t.Generator[t.Tuple[str, T], None, None]


@dataclasses.dataclass
class Node(t.Generic[T]):
    """Topology relations representation"""

    content: T
    children: list


class Tree(dict[str, Node[T]]):
    """Generic tree builder"""

    def __init__(self):
        super().__init__()
        self.__root_nodes_list: list[Node[T]] = []

    def put(self, items: t.Iterable[t.Tuple[str, T]], *, parent_name: t.Optional[str] = None) -> None:
        """Put items into the topology"""
        nodes_list: list[Node[T]] = []
        for name, item in items:
            node: Node[T] = Node(content=item, children=[])
            nodes_list.append(node)
            self[name] = node
        if parent_name is None:
            self.__root_nodes_list.extend(nodes_list)
        else:
            self[parent_name].children.extend(nodes_list)

    def generate_ascii_representation(self) -> AsciiLinesGeneratorType:
        """Generate tree representation components. A component is a pair of:
        - Prefix: a string containing aligned ASCII box drawing symbols, respective to the tree node graph
        - Object: the content of the corresponding node
        """
        yield from self._internal_tree_generate(nodes=self.__root_nodes_list, prefix=None)

    def _internal_tree_generate(self, nodes: list[Node[T]], prefix: t.Optional[str]) -> AsciiLinesGeneratorType:
        last_node_num: int = len(nodes) - 1
        for num, node in enumerate(nodes):
            is_last_node: bool = num == last_node_num
            if prefix is None:
                yield "", node.content
                yield from self._internal_tree_generate(
                    nodes=node.children,
                    prefix="",
                )
            else:
                yield prefix + ("└──" if is_last_node else "├──"), node.content
                yield from self._internal_tree_generate(
                    nodes=node.children,
                    prefix=prefix + ("   " if is_last_node else "│  "),
                )


def get_common_prefix(*strings: str) -> str:
    """Calculate the longest common prefix of a sequence of strings"""
    character_tuples: t.Iterable[t.Tuple[str, ...]] = zip(*strings)
    common_prefix_iterator = itertools.takewhile(lambda chars: all(chars[0] == c for c in chars), character_tuples)
    return "".join(common_chars[0] for common_chars in common_prefix_iterator)


def locate_parent_name_by_prefix(children: t.Iterable[str], candidates: t.Iterable[str]) -> str:
    """Define the optimal parent among candidates for the children"""
    longest_match_length: int = -1
    sources_common_prefix: str = get_common_prefix(*children)
    optimal_item_name: str = ""
    for candidate in candidates:
        match_length = len(get_common_prefix(candidate, sources_common_prefix))
        if match_length > longest_match_length:
            longest_match_length = match_length
            optimal_item_name = candidate
        elif match_length == longest_match_length and len(optimal_item_name) > len(candidate):
            optimal_item_name = candidate
    return optimal_item_name
