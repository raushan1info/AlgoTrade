"""Run a long/flat strategy on one exact F&O contract using configured market data."""
import argparse
import json
from datetime import date
from pathlib import Path

from backtesting.derivatives_engine import DerivativesBacktestConfig, run_derivative_backtest
from core.base.derivatives import DerivativeContract
from core.configuration.loader import REPOSITORY_ROOT, load_catalog
from data.registry import create_provider
from strategies.registry import create_strategy


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research backtest for one exact futures/options contract (no order execution)."
    )
    parser.add_argument("--provider", default="groww_fno", help="Provider ID in config/providers.yaml")
    parser.add_argument("--symbol", required=True, help="Exact provider contract symbol")
    parser.add_argument("--underlying", required=True, help="Underlying, e.g. NIFTY")
    parser.add_argument("--kind", choices=("future", "option"), required=True)
    parser.add_argument("--expiry", required=True, help="Contract expiry YYYY-MM-DD")
    parser.add_argument("--lot-size", type=int, required=True, help="Verified lot size for this expiry")
    parser.add_argument("--tick-size", type=float, required=True, help="Verified tick size for this contract")
    parser.add_argument("--strike", type=float, default=None, help="Required for options")
    parser.add_argument("--option-type", choices=("CE", "PE"), default=None)
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--strategy", default="rsi_14", help="Strategy ID in config/strategies.yaml")
    parser.add_argument("--lots", type=int, default=1)
    parser.add_argument("--initial-capital", type=float, default=100_000)
    parser.add_argument("--transaction-cost-bps", type=float, default=0)
    parser.add_argument("--slippage-bps", type=float, default=0)
    parser.add_argument(
        "--futures-margin-rate", type=float, default=None,
        help="Explicit approximate margin fraction for futures; required for futures only",
    )
    parser.add_argument("--output", default=None, help="Output CSV path")
    args = parser.parse_args()

    try:
        start_date, end_date, expiry = (
            date.fromisoformat(args.start), date.fromisoformat(args.end), date.fromisoformat(args.expiry)
        )
    except ValueError as exc:
        parser.error(f"Dates must use YYYY-MM-DD: {exc}")
    if start_date > end_date:
        parser.error("--start must be on or before --end")
    if args.kind == "option" and (args.strike is None or args.option_type is None):
        parser.error("Options require both --strike and --option-type")
    if args.kind == "future" and (args.strike is not None or args.option_type is not None):
        parser.error("Futures must not specify --strike or --option-type")

    catalog = load_catalog()
    if args.provider not in catalog["providers"]:
        parser.error(f"Unknown provider '{args.provider}'")
    if args.strategy not in catalog["strategies"]:
        parser.error(f"Unknown strategy '{args.strategy}'")
    provider = create_provider(args.provider, catalog["providers"][args.provider])
    market_data = provider.get_history(args.symbol, args.start, args.end)
    contract = DerivativeContract(
        instrument_id=args.symbol,
        underlying=args.underlying,
        exchange="NSE" if args.symbol.upper().startswith("NSE-") else "NSE",
        segment="FNO",
        expiry=expiry,
        lot_size=args.lot_size,
        tick_size=args.tick_size,
        kind=args.kind,
        strike=args.strike,
        option_type=args.option_type,
    )
    config = DerivativesBacktestConfig(
        initial_capital=args.initial_capital,
        lots=args.lots,
        transaction_cost_bps=args.transaction_cost_bps,
        slippage_bps=args.slippage_bps,
        futures_margin_rate=args.futures_margin_rate,
    )
    strategy = create_strategy(args.strategy, catalog["strategies"][args.strategy])
    results, metrics = run_derivative_backtest(market_data, strategy, contract, config)
    output = Path(args.output) if args.output else (
        REPOSITORY_ROOT / "reports" / "derivatives" / f"{args.symbol.replace('/', '_')}_{args.strategy}.csv"
    )
    if not output.is_absolute():
        output = REPOSITORY_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index_label="Date")
    summary_path = output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Results: {output}")
    print(f"Summary: {summary_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
