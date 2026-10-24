# Implementation Plan: Reliable Multi-Instrument Research and Watchlist

## Outcome

AlgoTrade should be a local-first, configuration-driven research tool. After a user installs dependencies, configures one supported market-data provider and supplies valid credentials, a single command should validate provider/data readiness, run configured equity/index research, and produce a reproducible daily watchlist. Derivatives are a separate workflow because an underlying index history is not an option/futures contract history.

This is an engineering acceptance checklist, not a claim that all items are already implemented. The CLI must fail loudly when required data or metadata is unavailable; it must never substitute synthetic data silently.

## Operating principles

- Keep the current modular monolith. No `frontend/`, `llm/`, or `api/` layer is needed for this milestone.
- Keep strategy logic pure and provider-independent. Provider adapters fetch data; validators normalize it; backtest engines model fills/costs; reports explain results.
- Keep IDs provider-neutral. Map each logical dataset to provider-specific symbol, exchange, segment and interval in YAML.
- Never commit real tokens, API keys, cookies, or account data. Use root `.env` / process environment.
- Treat historical data, current signals, simulated trades and live orders as different concepts.
- Use explicit `data_status`, `source`, `as_of`, and assumptions in every report.
- Do not infer F&O availability from an index existing. Use an exchange/broker contract catalog and the contract's dated metadata.
- Do not enable live order placement as part of this PR.

## Target user workflow

1. Install: `python -m pip install -e '.[dev,zerodha]'` or the supported provider extra.
2. Copy `.env.example` to `.env`; set credentials and access token for the chosen provider.
3. Edit `config/providers.yaml` and `config/datasets.yaml` to map logical datasets to provider-specific symbols.
4. Edit `config/research_universe.yaml` to enable desired index/equity datasets and strategies.
5. Run `python scripts/run_watchlist.py validate` to check config, credentials and provider readiness.
6. Run `python scripts/run_watchlist.py run` to fetch fresh data, validate it, run the strategy/backtest matrix, and write CSV/Markdown reports.
7. For F&O, first discover dated contracts, verify expiry/lot/tick/instrument identity, and run a separate contract-level workflow. An underlying index API history is not enough to backtest options.

## Scope and acceptance gates

### Gate A — Configuration and provider readiness
- [ ] Every dataset resolves to exactly one provider and provider-specific symbol.
- [ ] Provider required environment variables are named in config; missing/placeholder credentials produce actionable errors.
- [ ] Smoke tests distinguish auth failure, unsupported symbol, no history, rate limiting and malformed payload where the provider exposes enough detail.
- [ ] Requested start/end dates are validated; end-date semantics are consistent and documented.
- [ ] Failed datasets cannot be silently replaced with synthetic data.
- [ ] API usage respects provider terms, permissions, rate limits and historical coverage.

### Gate B — Data integrity
- [ ] Normalize timestamps with an explicit exchange-local/timezone convention; do not mix dates/timezones silently.
- [ ] Validate OHLCV, sorted unique timestamps, duplicate candles, nulls, impossible price ranges and non-finite values.
- [ ] Detect suspicious gaps relative to an exchange calendar; weekends/holidays must not be treated as missing sessions.
- [ ] Record source, fetch timestamp, date range, row count, latest bar timestamp and warnings.
- [ ] Index, equity, futures and options series have explicit instrument types and are not mixed.
- [ ] Synthetic datasets remain test fixtures only and are labelled synthetic in every report.

### Gate C — Equity/index execution and backtesting
- [ ] A signal computed at candle close cannot fill on that same close unless a valid closing-auction model is explicit.
- [ ] Model fills at a configurable next-bar executable price (default next open for daily bars), with gaps represented.
- [ ] Charge entry, exit and final-liquidation costs; distinguish spread/slippage from fees.
- [ ] Reject invalid signal ranges and invalid price/capital states.
- [ ] Report trades, exposure, turnover, total return, CAGR, volatility, Sharpe, max drawdown, benchmark comparison, costs and data window.
- [ ] Add tests for no look-ahead, next-open fills, overnight gaps, position changes, end-of-test liquidation and costs.

### Gate D — Research quality
- [ ] Support one strategy over many datasets and many strategies over one dataset using a configurable matrix.
- [ ] Use chronological train/validation/test or walk-forward evaluation for tuned parameters; do not select parameters on the final test period.
- [ ] Report performance by market regime and out-of-sample period; include trade count and uncertainty warnings.
- [ ] Compare with a relevant benchmark on the same period and state whether benchmark costs are included.
- [ ] Do not claim profitability or recommendation from one backtest or synthetic data.

### Gate E — Daily watchlist
- [ ] Display instrument, provider, latest bar/as-of time, fast/slow MA, current state, new crossover event, signal age, data freshness and validation status.
- [ ] Rank by transparent configurable criteria; do not use an unexplained single "AI confidence" score.
- [ ] Separate technical signal state from trade eligibility and risk.
- [ ] Include reasons to watch, reasons for caution, and invalidation conditions.
- [ ] Generate CSV and Markdown with run ID and configuration/data provenance.
- [ ] One bad symbol should not prevent the rest of the configured universe from reporting; failures must be visible and summarized.

### Gate F — F&O contract research
- [ ] Resolve contract identity from a dated instrument master: exchange, segment, underlying, expiry, strike, CE/PE/future type, lot size, tick size, and provider token/symbol.
- [ ] Keep historical contract metadata point-in-time; current lot sizes/symbols must not be applied retrospectively.
- [ ] Model futures mark-to-market/margin separately from option premium P&L.
- [ ] Options require the selected contract's own historical premium data; an underlying signal alone cannot produce option P&L.
- [ ] State whether strategy is long option, short option, futures, or a multi-leg position.
- [ ] Model contract roll, expiry/settlement, exercise/assignment and relevant costs before calling results decision-grade.
- [ ] Costs must be date-aware/configurable and include applicable brokerage, exchange charges, STT, GST, stamp duty and other levies for instrument/side/date.
- [ ] Margin must come from a documented source for the relevant date/contract; a user-supplied fraction is only an experimental approximation.
- [ ] Until these gates pass, label F&O output experimental and not for live-trading decisions.

### Gate G — Risk, paper trading and operations (later milestone)
- [ ] Position sizing, max per-trade risk, max daily loss, max drawdown, exposure limits and kill switch.
- [ ] Paper-trading order lifecycle: submitted, acknowledged, rejected, partially filled, filled, cancelled; idempotency and reconciliation.
- [ ] Persist intended positions and reconcile against broker-reported positions before future live execution.
- [ ] Monitor stale data, failed jobs, rejected orders, abnormal slippage and P&L discrepancies.
- [ ] Live order placement remains disabled until separately reviewed, tested and explicitly requested.

## PR implementation order

1. Deliver a config-driven multi-instrument watchlist CLI and per-dataset failure isolation.
2. Correct the general backtest execution model and add regression tests for next-open fills and costs.
3. Expand the underlying index catalog; provider symbols remain explicitly configurable and F&O eligibility must be verified, not inferred.
4. Add provider connectivity smoke tests and stronger data provenance/freshness reporting.
5. Improve the F&O engine only after execution and contract metadata assumptions are testable; keep unsupported features explicitly blocked.
6. Run Ruff and pytest on Python 3.10, 3.11 and 3.12. Passing CI is required before calling the PR validated.

## Definition of done

- A clean checkout installs and runs documented commands.
- Config validation is deterministic and independent of the current working directory.
- No secrets or synthetic data are mistaken for real data.
- Reports can be reproduced from recorded config, provider, symbol, period, strategy parameters and code version.
- Every configured combination produces a result or a visible, actionable error row.
- README distinguishes implemented, experimental and future capabilities.
- CI passes on the latest PR head.

## What "just add API credentials" does and does not mean

Credentials are only one prerequisite. The user must select a provider whose plan supports the required instrument/history, configure its symbol/segment mapping, and maintain provider-specific tokens (some expire regularly). F&O requires a dated contract catalog and the exact contract's own data. The application should minimize manual setup, validate remaining blockers, and explain them rather than claiming credentials alone guarantee coverage.

## Implemented in this PR branch (not yet equivalent to production readiness)

- Added a YAML-configured daily watchlist matrix that can discover NIFTY/SENSEX index instruments from the Kite NSE/BSE instrument masters and run four configured strategies, plus CSV/Markdown output and per-dataset/per-strategy error rows.
- Added a validation command that checks catalog references and reports missing/placeholder provider credentials without making network requests.
- Updated the equity and experimental exact-contract F&O engines so close-derived signals are applied at the next bar's open; overnight gaps belong to the previously held position and open-to-close moves belong to the new position.
- Added configurable equity slippage basis points, end-of-test liquidation costs, and regression tests for gap/entry timing and final exit costs.
- Added setup documentation. Provider symbol coverage, current index support, dated F&O contract masters, statutory charges, and production-grade order/fill simulation still require verification and further implementation.

- Added a Kite derivative-contract discovery foundation that reads current NFO/BFO instrument-master metadata (expiry, strike, CE/PE/FUT, lot size, tick size and instrument token), filters expired contracts, and fetches exact-contract candles by token. This is current-master discovery only; it does not reconstruct expired historical contracts or choose an option trade.
