"""
Common types.
"""

from .display.base import BaseDisplay
from .loader.base import AbstractBaseWorkflowLoader
from .strategy.base import BaseStrategy

LoaderClassType = type[AbstractBaseWorkflowLoader]
StrategyClassType = type[BaseStrategy]
DisplayClassType = type[BaseDisplay]
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
