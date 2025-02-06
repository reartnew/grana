"""Colorizing utils"""

import re
import typing as t

from ..config.constants import C

__all__ = [
    "Color",
]


class Color:
    """Text color wrapping"""

    _COLOR_RE: t.Pattern = re.compile(r"([^\n]+)")

    @classmethod
    def gray(cls, message: str) -> str:
        """Make a string gray"""
        return cls._add_formatting(message, 90)

    @classmethod
    def red(cls, message: str) -> str:
        """Make a string red"""
        return cls._add_formatting(message, 31)

    @classmethod
    def green(cls, message: str) -> str:
        """Make a string green"""
        return cls._add_formatting(message, 32)

    @classmethod
    def yellow(cls, message: str) -> str:
        """Make a string yellow"""
        return cls._add_formatting(message, 33)

    @classmethod
    def blue(cls, message: str) -> str:
        """Make a string blue"""
        return cls._add_formatting(message, 34)

    @classmethod
    def bold(cls, message: str) -> str:
        """Make a string bold"""
        return cls._add_formatting(message, 1)

    @classmethod
    def _add_formatting(cls, message: str, code: int) -> str:
        if not C.USE_COLOR:
            return message
        return cls._COLOR_RE.sub(f"\u001b[{code}m\\1\u001b[0m", message)
