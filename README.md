# AlgoTrade

A modular Python framework for Indian equity research, strategy evaluation and (later) paper trading. The project starts as a local-first modular monolith: no frontend or API is required for the initial milestones.

## Current MVP

- Provider interface and OHLCV data validation
- Deterministic synthetic data provider for offline development
- Optional Yahoo Finance daily history provider
- Long-only moving-average crossover baseline
- Next-bar signal application to avoid same-bar look-ahead
- Transaction-cost modeling in basis points
- Return, CAGR, volatility, Sharpe ratio and maximum drawdown metrics
- Markdown summary and daily CSV output
- Automated tests

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"
python scripts/run_backtest.py
pytest
```

The default run uses synthetic data and does not require internet access. It writes `reports/backtest_report.md` and `reports/backtest_results.csv`.

## Use public market data (optional)

```bash
pip install -e ".[market-data]"
python scripts/run_backtest.py --provider yfinance --symbol RELIANCE.NS --start 2018-01-01 --end 2025-12-31
```

Yahoo Finance is an optional convenience source, not a guaranteed production-grade feed. Verify data quality, availability and applicable terms before relying on or redistributing it.

## Customize a backtest

```bash
python scripts/run_backtest.py --symbol DEMO.NS --fast-window 20 --slow-window 50 --capital 100000 --cost-bps 10
```

## Repository boundaries

- `core/`: shared models, validation and provider contracts
- `data/providers/`: market data implementations
- `strategies/`: signal generation only; no broker orders
- `backtesting/`: strategy simulation and costs
- `analytics/`: performance metrics
- `reporting/`: Markdown and CSV outputs
- `scripts/`: runnable commands
- `tests/`: automated checks
- `docs/`: architecture and implementation roadmap

See [Architecture](docs/ARCHITECTURE.md) and [Implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Important limitations

This is an educational research prototype, not investment advice or a production trading system. Synthetic data only validates software behavior. The current backtester is long-only and does not yet fully model slippage, taxes, exchange charges, liquidity, corporate actions, survivorship bias or execution failures. Do not use it for live trading without further validation, risk controls and compliance review.
