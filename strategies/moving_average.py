"""Moving-average crossover strategy."""
import pandas as pd
from strategies.base import BaseStrategy


class MovingAverageStrategy(BaseStrategy):
    def __init__(self, fast_window: int = 20, slow_window: int = 50):
        if fast_window < 1 or slow_window < 2 or fast_window >= slow_window:
            raise ValueError("Require 1 <= fast_window < slow_window")
        self.fast_window = fast_window
        self.slow_window = slow_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=data.index)
        result["fast_ma"] = data["Close"].astype(float).rolling(
            self.fast_window, min_periods=self.fast_window).mean()
        result["slow_ma"] = data["Close"].astype(float).rolling(
            self.slow_window, min_periods=self.slow_window).mean()
        result["signal"] = (result["fast_ma"] > result["slow_ma"]).astype(float)
        result.loc[result["slow_ma"].isna(), "signal"] = 0.0
        return result
