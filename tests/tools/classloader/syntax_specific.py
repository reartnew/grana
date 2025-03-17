"""Syntax-specific sources"""

import dataclasses


@dataclasses.dataclass
class SimplifiedUnion:
    """Use simplified syntax for union"""

    foo: str | float  # type: ignore[syntax]  # pylint: disable=unsupported-binary-operation
