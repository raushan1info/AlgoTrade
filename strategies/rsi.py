"""Relative Strength Index mean-reversion strategy."""
import pandas as pd
from strategies.base import BaseStrategy


class RSIStrategy(BaseStrategy):
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        if period < 2:
            raise ValueError("RSI period must be >= 2")
        if not 0 <= oversold < overbought <= 100:
            raise ValueError("Require 0 <= oversold < overbought <= 100")
        self.period, self.oversold, self.overbought = period, oversold, overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["Close"].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / self.period, min_periods=self.period,
                                       adjust=False).mean()
        loss = -delta.clip(upper=0).ewm(alpha=1 / self.period, min_periods=self.period,
                                        adjust=False).mean()
        relative_strength = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + relative_strength))
        rsi = rsi.mask((loss == 0) & (gain > 0), 100)
        rsi = rsi.mask((gain == 0) & (loss > 0), 0)
        result = pd.DataFrame(index=data.index)
        result["rsi"] = rsi
        signal = pd.Series(0.0, index=data.index)
        holding = False
        for idx, value in rsi.items():
            if pd.notna(value):
                if not holding and value < self.oversold:
                    holding = True
                elif holding and value > self.overbought:
                    holding = False
            signal.loc[idx] = float(holding)
        result["signal"] = signal
        return result
