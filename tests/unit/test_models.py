import pandas as pd
import pytest

from core.base.models import validate_ohlcv


def test_validate_ohlcv_rejects_missing_columns():
    with pytest.raises(ValueError, match="Missing OHLCV"):
        validate_ohlcv(pd.DataFrame({"Close": [100]}))



def test_ohlcv_rejects_non_finite_prices():
    frame = pd.DataFrame({
        "Open": [10.0], "High": [float("inf")], "Low": [9.0],
        "Close": [10.0], "Volume": [100],
    }, index=pd.to_datetime(["2024-01-01"]))
    with pytest.raises(ValueError, match="finite"):
        validate_ohlcv(frame)


def test_ohlcv_rejects_inconsistent_high_low():
    frame = pd.DataFrame({
        "Open": [10.0], "High": [9.0], "Low": [8.0],
        "Close": [8.5], "Volume": [100],
    }, index=pd.to_datetime(["2024-01-01"]))
    with pytest.raises(ValueError, match="High >="):
        validate_ohlcv(frame)
