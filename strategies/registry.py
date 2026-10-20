"""Strategy factory registry."""
from typing import Any
from strategies.base import BaseStrategy
from strategies.macd import MACDStrategy
from strategies.moving_average import MovingAverageStrategy
from strategies.rsi import RSIStrategy

STRATEGIES: dict[str, type[BaseStrategy]] = {
    "moving_average": MovingAverageStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
}


def create_strategy(strategy_id: str, definition: dict[str, Any]) -> BaseStrategy:
    strategy_type = definition.get("type")
    if strategy_type not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy type '{strategy_type}' for '{strategy_id}'. "
            f"Available: {', '.join(sorted(STRATEGIES))}"
        )
    parameters = definition.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError(f"Strategy '{strategy_id}' parameters must be a mapping")
    try:
        return STRATEGIES[strategy_type](**parameters)
    except TypeError as exc:
        raise ValueError(f"Invalid parameters for strategy '{strategy_id}': {exc}") from exc
