# AlgoTrade Roadmap

This roadmap is the durable checklist for future work. Keep it updated as each phase is implemented, tested with real data, and reviewed. Passing CI alone does not mean provider connectivity, market-data quality, or trading assumptions have been validated.

## Current checkpoint — PR #3: Watchlist and F&O research foundations

**Status:** Implemented on the open PR branch; CI passed. Awaiting user review and real-provider testing.

- [x] Configuration-driven watchlist and strategy/dataset matrix.
- [x] Provider adapters and validation command.
- [x] Equity backtest next-bar-open execution, costs, benchmark and regression tests.
- [x] Current-master F&O contract discovery, deterministic candidate selection, and research-only candidate reports.
- [ ] User verifies installation/configuration and runs commands with valid provider credentials.
- [ ] Confirm actual provider coverage, permissions, index symbols, candle ranges and report outputs.
- [ ] Record failures/results before starting the next implementation phase.

**Checkpoint rule:** Do not treat synthetic demos or CI-only success as evidence that real market data works.

## Phase 3 — Real-data validation and provenance (next PR after PR #3 testing)

**Suggested PR title:** Real-data validation and backtesting quality

- [ ] Add a reusable data-quality report for every dataset: provider/source, instrument, exchange/interval, requested and actual date range, row count, latest candle, fetch time and warnings.
- [ ] Validate timestamp timezone/session conventions, sorting, duplicate candles, null/non-finite values, OHLC relationships, volume anomalies and suspicious gaps against exchange sessions.
- [ ] Clearly distinguish weekends/holidays from missing market sessions.
- [ ] Test provider authentication, unsupported instruments, no history, rate limits and malformed responses where distinguishable.
- [ ] Verify stale-data thresholds and end-date semantics; fail clearly or mark a dataset unusable when required checks fail.
- [ ] Preserve per-dataset failure isolation and actionable error rows.
- [ ] Add fixture-based unit/integration tests and a documented manual smoke test using real credentials without committing secrets.
- [ ] Record provider limitations, licensing/terms and historical-data availability.

**Exit criteria:** Real-data runs are reproducible, data quality is visible, and bad/stale data cannot silently produce trusted-looking results.

## Phase 4 — Strategy evaluation and backtest research quality

- [ ] Standardize metrics and definitions: total return, CAGR, volatility, Sharpe, drawdown, turnover, exposure, trade count, costs and benchmark results.
- [ ] Add no-look-ahead and temporal-alignment regression tests.
- [ ] Add chronological train/validation/test or walk-forward evaluation for parameter tuning.
- [ ] Include out-of-sample and market-regime results; avoid tuning on the final test period.
- [ ] Add parameter sensitivity and robustness checks, and warn on small trade counts or insufficient history.
- [ ] Compare strategies and buy-and-hold over the same dates with explicit benchmark/cost assumptions.
- [ ] Record run ID, code version, configuration snapshot, provider, data window and strategy parameters in each report.

**Exit criteria:** Strategy comparisons are fair, reproducible and include out-of-sample evidence; no single backtest is presented as proof of profitability.

## Phase 5 — F&O historical and risk realism

- [ ] Build/archive point-in-time instrument-master snapshots, including historical expiries, lot sizes, tick sizes and contract identifiers.
- [ ] Fetch and validate the exact selected contract's own historical premium/price data; synchronize it with underlying signals.
- [ ] Add bid/ask or liquidity checks, open interest/volume where available, spread/slippage assumptions and premium affordability.
- [ ] Model futures mark-to-market separately from option premium P&L.
- [ ] Add date-aware statutory costs and documented margin assumptions.
- [ ] Implement and test expiry, roll, settlement and relevant exercise/assignment behavior.
- [ ] Test contract identity, missing history, expired contracts and survivorship/look-ahead risks.
- [ ] Keep unsupported strategy types (including short options and multi-leg strategies) explicitly blocked until implemented and tested.

**Exit criteria:** F&O results are only promoted beyond experimental status when contract history, fills, costs, margin and expiry behavior are supported by evidence. Current-master candidate selection alone does not satisfy this gate.

## Phase 6 — Paper trading and operational safety

- [ ] Define paper-trading order/position lifecycle and persist intended positions.
- [ ] Track submitted, acknowledged, rejected, partially filled, filled and cancelled states.
- [ ] Add idempotency, reconciliation, position/exposure limits, per-trade risk, daily-loss and drawdown limits, and a kill switch.
- [ ] Monitor stale data, job failures, rejected orders, unexpected slippage and P&L discrepancies.
- [ ] Test restart/recovery and duplicate-run behavior.
- [ ] Produce daily run summaries and actionable failure notifications.

**Exit criteria:** Paper trading runs reliably and risk controls/reconciliation are tested. Live order placement remains disabled until a separate explicit review and approval.

## Phase 7 — Scheduling and maintainability

- [ ] Add controlled scheduling only after the underlying commands are reliable.
- [ ] Use unique run IDs, structured logs, configuration/version snapshots and clear failure statuses.
- [ ] Make retries bounded and safe; avoid duplicate side effects.
- [ ] Document setup, token refresh, troubleshooting, data licensing and recovery procedures.

## Phase 8 — Optional research assistant / AI

This is deliberately deferred until the data and research pipeline is trustworthy.

- [ ] Define use cases such as explaining a report, summarizing company/sector context, or answering questions from sourced research outputs.
- [ ] Ground generated claims in traceable data and citations; show data freshness and uncertainty.
- [ ] Keep model output separate from validated metrics and deterministic strategy logic.
- [ ] Add evaluation, hallucination checks, audit logs and clear non-investment-advice limitations.
- [ ] Do not let an LLM place trades or bypass risk controls.

## Rules for every future PR

1. Keep PRs focused on one phase or a tightly related set of acceptance criteria.
2. Add tests and update this roadmap plus relevant architecture/setup docs in the same PR.
3. Run Ruff and pytest on supported Python versions; CI must pass.
4. Clearly label each item as implemented, experimental, blocked or future work.
5. Never commit credentials, and never silently substitute synthetic data for failed real data.
6. Update the status/checklists here after implementation and record any deferred items.
7. Do not enable live trading just because earlier phases pass.

## Related documentation

- [Implementation plan and engineering acceptance gates](IMPLEMENTATION_PLAN.md)
- [Real market-data setup](REAL_MARKET_DATA.md)
- [F&O architecture and limitations](FNO_ARCHITECTURE.md)