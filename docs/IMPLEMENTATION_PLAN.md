# AlgoTrade implementation plan

## Milestone 1 — Runnable research/backtesting MVP

- [x] Python project configuration and development dependencies
- [x] Provider-independent OHLCV validation and provider interface
- [x] Offline deterministic market-data provider
- [x] Optional Yahoo Finance provider
- [x] Long-only moving-average baseline strategy
- [x] Next-bar signal application and transaction-cost modeling
- [x] Core performance metrics and CSV/Markdown report
- [x] Unit tests for data, strategy and backtest behavior

## Current scope and limitations

This is a research prototype, not a production trading system. The initial backtester is long-only, uses daily close-to-close returns, assumes fractional position exposure, and models costs as basis points on position turnover. It does not yet model taxes, exchange charges, slippage, liquidity, circuit limits, corporate-action edge cases, survivorship bias or broker order execution. Synthetic-price results validate software behavior only; they are not investment performance.

## Next milestones

1. Data quality and reproducibility: data cache, provider metadata, trading calendar, corporate-action policy and data-quality reports.
2. Backtest realism: benchmark comparison, drawdown analysis, slippage/fees/taxes, position sizing, trade ledger and out-of-sample evaluation.
3. Indian equity research: NSE symbol master, fundamentals/financial statements, valuation metrics and source/licensing documentation.
4. Portfolio and risk: allocation constraints, exposure limits, concentration controls and portfolio-level backtesting.
5. Paper trading: broker adapter interface, order lifecycle, reconciliation, alerts and restart/recovery tests. Live trading only after explicit safety and compliance review.
6. Future optional interfaces: API, frontend and LLM modules can be added without changing strategy/backtest contracts.

## Reproducibility

The default demo uses deterministic synthetic data and works offline. Use the optional yfinance dependency to fetch public market data for experimentation. Check source terms and limitations before redistributing or commercializing data.
