# AlgoTrade

Modular, configuration-driven Indian equity research and backtesting framework.

## Quick start

```bash
python -m pip install -e '.[dev]'
python scripts/run_experiment.py list
python scripts/run_experiment.py validate --experiment compare_strategies
python scripts/run_experiment.py run --experiment compare_strategies
```

The default demos use synthetic data and are for testing plumbing only, not for investment conclusions.

## Real market data

Read [docs/REAL_MARKET_DATA.md](docs/REAL_MARKET_DATA.md) for Zerodha Kite Connect and Groww setup, placeholder credentials, real-data configuration, and Groww historical F&O contract catalog sync. No real broker credentials should be committed. The adapters in this milestone are read-only.

## Current scope

- Provider-neutral daily OHLCV research and strategy comparison.
- Synthetic, Yahoo Finance, CSV, generic REST JSON, Zerodha Kite Connect, and Groww historical-data providers.
- Buy-and-hold benchmark, transaction-cost-aware equity backtests, metrics, and local reports.
- Groww historical F&O expiry/contract symbol retrieval and CSV snapshots.

Not yet a production trading system: intraday backtesting, live streaming, order execution, point-in-time F&O master normalization, lot-based derivatives P&L, margin, expiry/settlement, complete Indian transaction charges, and broker order safety controls remain future work.
