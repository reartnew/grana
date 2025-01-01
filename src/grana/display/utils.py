import typing as t
import itertools


def _get_common_prefix(*strings: str) -> str:
    character_tuples: t.Iterable[t.Tuple[str, ...]] = zip(*strings)
    common_prefix_iterator = itertools.takewhile(lambda chars: all(chars[0] == c for c in chars), character_tuples)
    return "".join(common_chars[0] for common_chars in common_prefix_iterator)


def locate_insert_position_py_prefix(
    source: t.Iterable[str], receiver: t.Iterable[str]
) -> t.Tuple[int, int]:
    slice_position: int = -1
    longest_match_length: int = -1
    sources_common_prefix: str = _get_common_prefix(*source)
    for receiver_position, receiver_item in enumerate(receiver):
        match_length = len(_get_common_prefix(receiver_item, sources_common_prefix))
        if match_length > longest_match_length:
            longest_match_length = match_length
            slice_position = receiver_position
    return slice_position, longest_match_length
