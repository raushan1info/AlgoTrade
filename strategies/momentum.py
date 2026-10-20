"""Long-only moving-average trend strategy."""
import pandas as pd


def generate_signals(prices: pd.Series, fast_window: int = 20, slow_window: int = 50) -> pd.DataFrame:
    if fast_window < 1 or slow_window < 2:
        raise ValueError("Moving-average windows must be positive and slow_window >= 2")
    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window")
    frame = pd.DataFrame({"close": prices.astype(float)})
    frame["fast_ma"] = frame["close"].rolling(fast_window, min_periods=fast_window).mean()
    frame["slow_ma"] = frame["close"].rolling(slow_window, min_periods=slow_window).mean()
    frame["signal"] = (frame["fast_ma"] > frame["slow_ma"]).astype(float)
    frame.loc[frame["slow_ma"].isna(), "signal"] = 0.0
    return frame
