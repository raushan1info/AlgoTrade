import pandas as pd
import pytest

from core.base.models import validate_ohlcv


def test_validate_ohlcv_rejects_missing_columns():
    with pytest.raises(ValueError, match="Missing OHLCV"):
        validate_ohlcv(pd.DataFrame({"Close": [100]}))
