# Real Market Data: Zerodha Kite Connect and Groww

This project supports read-only historical OHLCV retrieval from Zerodha Kite Connect and Groww. API keys in .env.example are placeholders; no working credentials are committed. Copy the file to .env and replace the relevant values locally.

## Choose a provider

- **Zerodha Kite Connect**: configure KITE_API_KEY and KITE_ACCESS_TOKEN. Install the SDK with `pip install -e '.[zerodha]'`. For historical candles, the Kite Connect plan must include historical-data access. Kite access tokens normally expire before the next trading day and need to be refreshed through the official login flow. KITE_API_SECRET is reserved for the authentication flow and is not used to fetch candles once a valid access token exists.
- **Groww**: configure GROWW_ACCESS_TOKEN. The adapter uses the current /v1/historical/candles endpoint with bearer authentication and X-API-VERSION: 1.0.

Neither adapter places orders. Broker execution, order management, live streaming, and automatic token refresh are intentionally out of scope for this milestone.

## Run

```bash
cp .env.example .env
# Edit .env locally; do not commit it.
python -m pip install -e '.[dev,zerodha]'
python scripts/run_experiment.py validate --experiment compare_strategies
```

To use real data, edit config/experiments.yaml and select reliance_zerodha or reliance_groww in the experiment's datasets list. The examples use NSE:RELIANCE for Kite and NSE-RELIANCE for Groww. Keep the synthetic demo as the default until credentials are configured.

## Sync historical F&O contract symbols

```bash
python scripts/sync_groww_contracts.py --underlying NIFTY --year 2025
python scripts/sync_groww_contracts.py --underlying BANKNIFTY --year 2025 --month 3
```

This writes a local CSV snapshot containing exchange, segment, underlying, expiry, contract symbol, and retrieval timestamp. It is a starting point for contract catalog ingestion, not a complete authoritative instrument master: it does not infer lot sizes, tick sizes, margin, settlement rules, or point-in-time validity.

## Run an exact-contract F&O research backtest

After configuring a Groww token and verifying the contract's expiry, lot size, and tick size from a trusted source, you can run a long/flat strategy on one historical contract:

```bash
python scripts/run_derivative_backtest.py \\
  --provider groww_fno \\
  --symbol NSE-NIFTY-30Sep25-24650-CE \\
  --underlying NIFTY --kind option \\
  --expiry 2025-09-30 --strike 24650 --option-type CE \\
  --lot-size YOUR_VERIFIED_LOT_SIZE --tick-size 0.05 \\
  --start 2025-09-01 --end 2025-09-30 --strategy rsi_14 \\
  --initial-capital 100000 --transaction-cost-bps 5 --slippage-bps 5
```

Replace the illustrative contract and metadata with values valid for the selected date; do not copy the example lot size or symbol blindly. The script writes a candle-level CSV and a JSON metrics summary. For futures, add `--futures-margin-rate` using a documented estimate for the selected contract/date. This margin fraction is only an approximation and does not replace exchange/broker SPAN, exposure, or intraday margin calculations.

The engine is intentionally limited to one exact contract and long/flat signals. It does not yet implement automatic expiry settlement, short options, synchronized underlying/option-chain features, realistic dynamic margin, or full Indian statutory costs. Do not use its results for live trading decisions.

## Limits and correctness notes

- The current experiment runner/backtester accepts **daily OHLCV only**. Intraday intervals must not be fed into the current daily annualized metrics/backtester.
- Groww historical requests are chunked into windows shorter than the documented 180-day daily request limit. Historical coverage depends on the provider's instrument, segment, plan, and API availability.
- Kite symbols can be a numeric instrument token or EXCHANGE:TRADING_SYMBOL. Symbol lookup uses a date-stamped local instrument-master cache. Expired derivative contracts require point-in-time contract masters; current instruments are not a substitute for historical contract identity.
- Groww's expiry and contracts endpoints retrieve historical F&O catalog entries, but a date-versioned normalized contract database and lot-based derivatives P&L engine are not implemented yet.
- Validate split/dividend adjustments, corporate actions, data gaps, delisted instruments, transaction taxes, slippage, lot sizes, expiry/settlement, and licensing before treating results as investment evidence or commercial output.
- API access and historical availability are governed by provider documentation and plan terms. Do not redistribute data unless your provider agreement permits it.

## Daily Nifty/Sensex research watchlist

The default `config/research_universe.yaml` enables automatic discovery of available NSE/BSE instrument-master entries whose index symbols begin with NIFTY or SENSEX. The runner uses each discovered instrument token and tests historical candles separately. Coverage depends on the provider, plan, symbol metadata and history availability; the CLI records unsupported symbols as visible errors rather than substituting synthetic data. The configured dataset list remains available as a static fallback if you set `discovery.enabled: false`.

```bash
python -m pip install -e '.[dev,zerodha]'
# Set KITE_API_KEY and a currently valid KITE_ACCESS_TOKEN in .env.
python scripts/run_watchlist.py validate
python scripts/run_watchlist.py run
```

The command writes `reports/watchlist/watchlist.csv` and `reports/watchlist/watchlist.md`. The default end date is the previous calendar day to avoid using a potentially incomplete daily candle. Use `--start YYYY-MM-DD --end YYYY-MM-DD` to override the period.

To use Groww instead, set `discovery.enabled: false` in `config/research_universe.yaml`, then change the selected static dataset mappings in `config/datasets.yaml` to `provider: groww_api`, use provider-supported symbols, and set the correct exchange/segment in `config/providers.yaml`. Configure `GROWW_ACCESS_TOKEN`. The current automatic instrument-master discovery is Kite-specific; do not assume a Kite symbol can be reused unchanged with Groww.

The watchlist is for underlying index signal research; it does not automatically choose a futures/options contract. F&O needs the exact contract's own historical prices and verified, date-appropriate contract metadata. Not every index has listed derivatives, and the provider's historical API may not return every index/contract.
