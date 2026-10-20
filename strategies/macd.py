"""Moving Average Convergence Divergence strategy."""
import pandas as pd
from strategies.base import BaseStrategy


class MACDStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        if min(fast_period, slow_period, signal_period) < 1 or fast_period >= slow_period:
            raise ValueError("Require positive periods and fast_period < slow_period")
        self.fast_period, self.slow_period, self.signal_period = (
            fast_period, slow_period, signal_period
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["Close"].astype(float)
        fast = close.ewm(span=self.fast_period, adjust=False,
                         min_periods=self.fast_period).mean()
        slow = close.ewm(span=self.slow_period, adjust=False,
                         min_periods=self.slow_period).mean()
        macd = fast - slow
        signal_line = macd.ewm(span=self.signal_period, adjust=False,
                               min_periods=self.signal_period).mean()
        result = pd.DataFrame(index=data.index)
        result["macd"] = macd
        result["signal_line"] = signal_line
        result["signal"] = (macd > signal_line).astype(float)
        result.loc[signal_line.isna(), "signal"] = 0.0
        return result
