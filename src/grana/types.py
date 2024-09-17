"""
Common types.
"""

import typing as t

from .display.base import BaseDisplay
from .loader.base import AbstractBaseWorkflowLoader
from .strategy import BaseStrategy

LoaderClassType = t.Type[AbstractBaseWorkflowLoader]
StrategyClassType = t.Type[BaseStrategy]
DisplayClassType = t.Type[BaseDisplay]
LoaderType = AbstractBaseWorkflowLoader
StrategyType = BaseStrategy
DisplayType = BaseDisplay

__all__ = [
    "LoaderClassType",
    "StrategyClassType",
    "DisplayClassType",
    "LoaderType",
    "StrategyType",
    "DisplayType",
]
