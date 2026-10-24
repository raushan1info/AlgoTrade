from pathlib import Path

import pandas as pd
import pytest

from core.configuration.loader import CONFIG_DIR, load_catalog
from scripts import run_watchlist as watchlist_module
from scripts.run_watchlist import (
    _load_watchlist,
    _period_dates,
    _resolve_dataset_items,
    _signal_summary,
)


def test_signal_summary_detects_bullish_crossover():
    frame = pd.DataFrame({
        "fast_ma": [99.0, 101.0],
        "slow_ma": [100.0, 100.0],
        "signal": [0.0, 1.0],
    })
    summary = _signal_summary(frame)
    assert summary["signal_event"] == "BULLISH_CROSSOVER"
    assert summary["signal_state"] == "LONG"
    assert summary["ma_spread_pct"] == pytest.approx(1.0)


def test_signal_summary_detects_bearish_crossover():
    frame = pd.DataFrame({"signal": [1.0, 0.0]})
    summary = _signal_summary(frame)
    assert summary["signal_event"] == "BEARISH_CROSSOVER"
    assert summary["signal_state"] == "FLAT"


def test_signal_summary_rejects_missing_signal_values():
    with pytest.raises(ValueError, match="missing signal"):
        _signal_summary(pd.DataFrame({"signal": [0.0, float("nan")]}))


def test_configured_watchlist_references_known_datasets_and_strategies():
    catalog = load_catalog(CONFIG_DIR)
    watchlist = _load_watchlist(Path(CONFIG_DIR))
    assert set(watchlist["datasets"]).issubset(catalog["datasets"])
    assert set(watchlist["strategies"]).issubset(catalog["strategies"])


def test_watchlist_uses_previous_completed_calendar_day_by_default():
    watchlist = _load_watchlist(Path(CONFIG_DIR))
    start, end, end_date = _period_dates(watchlist, None, None)
    assert start == watchlist["period"]["start"]
    assert end_date.isoformat() == end



def test_dynamic_discovery_creates_provider_neutral_dataset_items(monkeypatch):
    catalog = load_catalog(CONFIG_DIR)
    watchlist = _load_watchlist(Path(CONFIG_DIR))
    monkeypatch.setenv("KITE_API_KEY", "test-key")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "test-token")

    class FakeIndexProvider:
        def list_index_instruments(self, exchanges, prefixes):
            assert exchanges == ("NSE", "BSE")
            assert prefixes == ("NIFTY", "SENSEX")
            return pd.DataFrame({
                "exchange": ["NSE", "BSE"],
                "tradingsymbol": ["NIFTY 50", "SENSEX"],
                "instrument_token": [1001, 2001],
                "name": ["NIFTY 50", "SENSEX"],
            })

    monkeypatch.setattr(
        watchlist_module, "create_provider", lambda provider_id, config: FakeIndexProvider()
    )
    items = _resolve_dataset_items(catalog, watchlist, {})
    assert len(items) == 2
    assert items[0][1]["data_kind"] == "index"
    assert {item[1]["symbol"] for item in items} == {"1001", "2001"}
    assert {item[1]["display_symbol"] for item in items} == {"NSE:NIFTY 50", "BSE:SENSEX"}


def test_non_trend_strategy_uses_entry_exit_labels_not_crossover_labels():
    entry = _signal_summary(pd.DataFrame({"signal": [0.0, 1.0]}), "rsi")
    exit_signal = _signal_summary(pd.DataFrame({"signal": [1.0, 0.0]}), "rsi")
    assert entry["signal_event"] == "ENTRY_SIGNAL"
    assert exit_signal["signal_event"] == "EXIT_SIGNAL"
