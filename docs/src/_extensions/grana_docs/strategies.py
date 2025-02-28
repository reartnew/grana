from grana.strategy.base import STRATEGIES_MAP
from .base import GranaBaseDirective
from grana.config.constants.impl import StrategyClass

__all__ = [
    "GranaDefaultStrategyDirective",
    "GranaStrategiesListDirective",
]


class GranaDefaultStrategyDirective(GranaBaseDirective):

    def get_raw_text(self) -> str:
        default_strategy_name: str = StrategyClass().default().NAME
        return f"Default strategy is [](#{default_strategy_name})."


class GranaStrategiesListDirective(GranaBaseDirective):

    def get_raw_text(self) -> str:
        items: list[str] = []
        for strategy_name, strategy_class in STRATEGIES_MAP.items():
            items.append(f"### `{strategy_name}`\n\n{strategy_class.__doc__}")
        return "\n".join(items)
