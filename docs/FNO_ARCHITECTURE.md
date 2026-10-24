# Futures and Options (F&O) support

## Current status

The repository now defines provider-independent instrument and derivative-contract models, a contract-master interface, an exact-contract history interface, and an underlying index catalog for NIFTY 50, BANK NIFTY, FINNIFTY, and SENSEX. These are architectural foundations, not a functioning F&O data feed or options backtester. No current provider in this repository supplies a historical options chain or an authoritative dated contract master.

## Required layers

1. **Instrument master:** ingest exchange/broker contract files with effective dates, expiry, strike, CE/PE, lot size, tick size, exchange, segment, and provider instrument token. Retain historical snapshots; lot sizes and contract rules can change.
2. **Market data:** separate interfaces for underlying/index candles, futures candles, exact option-contract candles, and option-chain snapshots. Normalize timestamps and session calendars and record source/provenance.
3. **Contract selection:** strategies should express selection rules (expiry bucket, moneyness, delta, liquidity, strike interval) rather than hard-coded symbols. Selection must use only information available at decision time.
4. **F&O simulation:** model lot-based quantities, premium cashflows, margin, mark-to-market, expiry settlement, exercise/assignment rules where relevant, spreads, slippage, brokerage, STT, exchange/SEBI charges, GST, stamp duty, and applicable contract-specific rules. Costs must be versioned by date and segment.
5. **Risk:** enforce per-position and portfolio exposure, margin availability, loss limits, expiry/event rules, and gap risk. Option risk cannot be represented by the current long-only fractional-exposure equity engine.
6. **Research validation:** avoid look-ahead from end-of-day option-chain snapshots, survivorship from current-only contract masters, stale/illiquid quotes, and survivorship of expired contracts. Add out-of-sample evaluation and realistic fill assumptions.
7. **Execution:** paper trading first, then a separately implemented broker adapter with order lifecycle, retries, idempotency, reconciliation, kill switch, and audit logs. Keep live execution disabled until specifically designed and tested.

## Supported underlyings in the initial catalog

- NSE: NIFTY 50, BANK NIFTY, FINNIFTY
- BSE: SENSEX

The catalog deliberately does not hard-code lot sizes, expiry weekdays, strike intervals, or current contract symbols. Resolve these from a dated authoritative instrument master and applicable exchange specifications. Do not assume all underlyings have the same expiry schedule or contract rules.

## Suggested implementation phases

1. Select a licensed historical data source and broker/exchange instrument-master format.
2. Implement instrument-master ingestion and historical snapshots with tests.
3. Implement provider adapters for underlying and exact futures/options contracts.
4. Build an option-chain store with point-in-time timestamps and data-quality checks.
5. Add a separate lot-based futures/options backtest engine and a dated Indian-market cost model.
6. Add strategy examples (futures trend, option spreads, hedges) only after data and simulation semantics are validated.
7. Add paper trading and broker integration as a separate milestone.

This framework is for educational research, not investment advice. Options and futures can produce rapid and substantial losses; backtests are especially sensitive to data quality, fills, liquidity, and cost assumptions.
