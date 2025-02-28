from grana.strategy.base import STRATEGIES_MAP
from .base import GranaBaseDirective

__all__ = [
    "GranaStrategiesDirective",
]


class GranaStrategiesDirective(GranaBaseDirective):

    def get_raw_text(self) -> str:
        items: list[str] = []
        for strategy_name, strategy_class in STRATEGIES_MAP.items():
            items.append(f"### `{strategy_name}`\n\n{strategy_class.__doc__}")
        return "\n".join(items)
