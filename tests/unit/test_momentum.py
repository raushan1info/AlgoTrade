import numpy as np
import pandas as pd
import pytest

from strategies.momentum import generate_signals


def test_strategy_does_not_signal_before_slow_window():
    signals = generate_signals(pd.Series(np.arange(1, 101, dtype=float)), 3, 5)
    assert (signals["signal"].iloc[:4] == 0).all()
    assert (signals["signal"].iloc[4:] == 1).all()


def test_invalid_window_configuration_fails():
    with pytest.raises(ValueError, match="fast_window"):
        generate_signals(pd.Series(np.arange(1, 100, dtype=float)), 20, 10)
