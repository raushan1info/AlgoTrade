# AlgoTrade

Modular, configuration-driven Indian equity research and backtesting framework.

## Quick start

```bash
python -m pip install -e '.[dev,zerodha]'
python scripts/run_experiment.py list
python scripts/run_experiment.py validate --experiment compare_strategies
python scripts/run_experiment.py run --experiment compare_strategies
python scripts/run_watchlist.py validate
python scripts/run_watchlist.py run
python scripts/run_fno_candidates.py --help
python scripts/run_fno_candidates.py
```

The default demos use synthetic data and are for testing plumbing only, not for investment conclusions. The watchlist uses the configured real-data index datasets; failed or unsupported symbols are shown as errors rather than silently replaced with synthetic prices.

## Roadmap and implementation status

See [docs/ROADMAP.md](docs/ROADMAP.md) for the phased checklist, current checkpoint, next PR scope, acceptance criteria, and deferred work. See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for engineering acceptance gates and detailed limitations.

## Real market data

Read [docs/REAL_MARKET_DATA.md](docs/REAL_MARKET_DATA.md) for Zerodha Kite Connect and Groww setup, placeholder credentials, real-data configuration, and Groww historical F&O contract catalog sync. No real broker credentials should be committed. The adapters in this milestone are read-only.

## Current scope

- Provider-neutral daily OHLCV research and strategy comparison.
- Synthetic, Yahoo Finance, CSV, generic REST JSON, Zerodha Kite Connect, and Groww historical-data providers.
- Buy-and-hold benchmark, daily bar-based backtests with close-derived signals filled at the next open, configurable transaction costs/slippage, metrics, and local reports.
- Config-driven daily index/equity watchlist with per-dataset failure isolation and CSV/Markdown output.
- Groww historical F&O expiry/contract symbol retrieval and CSV snapshots.
- Separate experimental lot-based backtest for one exact option/futures contract, with explicit transaction costs, slippage, and capital/margin assumptions.
- Config-driven, research-only F&O candidate generation from underlying-index strategy states, with expiry/moneyness policy, contract metadata, and explicit unknown-liquidity warnings.

Not yet a production trading system: intraday equity backtesting, live streaming, order execution, authoritative point-in-time F&O master/lot-size ingestion, short-option strategies, realistic dynamic futures margin, expiry/settlement, complete date-versioned Indian transaction charges, and broker order safety controls remain future work. Index symbol availability and derivative eligibility depend on the selected provider and must be verified. The new F&O backtester is research-only, supports long/flat signals for one exact contract, and requires verified lot/tick sizes and explicit assumptions.