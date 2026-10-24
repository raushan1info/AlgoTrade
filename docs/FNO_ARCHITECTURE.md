# Futures and Options (F&O) support

## Current status

The repository defines provider-independent instrument/derivative models, Groww expiry and contract-symbol retrieval, exact-contract historical candles, and an underlying index catalog for NIFTY 50, BANK NIFTY, FINNIFTY, and SENSEX. It now also includes a separate research-only lot-based backtester for one exact option/futures contract. This is not a production F&O system: provider contract lists do not supply all dated lot/tick/margin/settlement metadata, and no point-in-time option-chain store exists.

## Experimental exact-contract backtest

Run `python scripts/run_derivative_backtest.py --help` for the full CLI. The script fetches candles from a configured provider and writes a result CSV plus JSON metrics. Supply an exact contract symbol, expiry, verified lot size/tick size, and (for options) strike and CE/PE. For futures, explicitly supply a documented approximate `--futures-margin-rate`; the engine intentionally does not assume one universal margin percentage.

The experimental engine applies close-derived signals at the next bar's open, attributes overnight gaps to the position held before that open, attributes open-to-close movement to the new position, and charges configurable turnover costs/slippage including end liquidation. This is still an OHLC bar approximation. Limitations: one exact contract per run; long/flat signals only; whole lots; no short options, spreads, automatic expiry/settlement, dynamic SPAN/exposure margin, date-versioned statutory charges, or broker fills. Option strategies currently generate signals from the option contract's own candle series, not from a synchronized underlying/option-chain model. Treat outputs as experimental until these gaps are addressed.

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

## Current Kite contract-discovery foundation

The Kite adapter now exposes `list_derivative_contracts(underlying, as_of, exchanges=("NFO", "BFO"))` and `get_contract_history(contract, start, end)`. It reads expiry, strike, CE/PE/FUT type, lot size, tick size, exchange/segment, and instrument token from the current broker instrument master. It filters out contracts expired on the requested date and resolves exact-contract candles by instrument token.

Important limits:
- This is discovery from the **current** instrument master, not an archived historical contract database. It cannot recover expired contracts absent from the current master and must not be used to claim point-in-time historical availability.
- The method lists contracts; it does not yet select a trade. An explicit policy is still needed for expiry bucket, ATM/OTM strike, liquidity/open interest, premium budget, and whether the strategy should use futures, calls, puts, or defined-risk spreads.
- Provider support, exact symbol conventions, historical candle availability, and applicable contract metadata must be tested against the authenticated account and provider plan before relying on results.
