# Architecture

The first version is a modular monolith: one Python project with explicit boundaries and no service/API layer.

- core/base: shared models and validation.
- core/market_data: provider contract consumed by the application.
- data/providers: offline synthetic and optional Yahoo Finance providers.
- strategies: pure signal-generation logic; strategies do not place orders.
- backtesting: applies signals with a one-bar delay and models transaction costs.
- analytics: return and risk metrics.
- reporting: exports daily results and a Markdown summary.
- scripts: command-line entry points.
- tests: automated behavior checks.

## Data flow

Provider -> OHLCV validation -> Strategy signals -> Backtest engine -> Metrics -> CSV/Markdown report

Future API, UI, LLM, broker and database integrations should call these stable Python interfaces rather than embedding business logic in interface layers.
