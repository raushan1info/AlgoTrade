"""Sync Groww historical F&O contract symbols into a local CSV snapshot.

This captures contract symbols and expiry metadata returned by Groww; it does not
invent lot sizes, tick sizes, margins, or historical contract-validity assumptions.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core.configuration.loader import REPOSITORY_ROOT, load_catalog
from data.registry import create_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Groww F&O contract symbols for an underlying.")
    parser.add_argument("--provider", default="groww_fno", help="Provider ID in config/providers.yaml")
    parser.add_argument("--underlying", required=True, help="Underlying symbol, e.g. NIFTY or BANKNIFTY")
    parser.add_argument("--year", type=int, required=True, help="Expiry year to retrieve")
    parser.add_argument("--month", type=int, default=None, help="Optional expiry month (1-12)")
    parser.add_argument("--output", default=None, help="Optional output CSV path")
    args = parser.parse_args()
    if args.month is not None and not 1 <= args.month <= 12:
        parser.error("--month must be between 1 and 12")

    catalog = load_catalog()
    if args.provider not in catalog["providers"]:
        parser.error(f"Unknown provider '{args.provider}'")
    provider = create_provider(args.provider, catalog["providers"][args.provider])
    if not hasattr(provider, "get_expiries") or not hasattr(provider, "get_contracts"):
        parser.error(f"Provider '{args.provider}' does not support Groww contract catalog endpoints")

    captured_at = datetime.now(timezone.utc).isoformat()
    rows = []
    expiries = provider.get_expiries(args.underlying, year=args.year, month=args.month)
    for expiry in expiries:
        for contract_symbol in provider.get_contracts(args.underlying, expiry):
            rows.append({
                "exchange": catalog["providers"][args.provider].get("exchange", "NSE"),
                "segment": "FNO",
                "underlying": args.underlying.upper(),
                "expiry": expiry.isoformat(),
                "contract_symbol": contract_symbol,
                "captured_at_utc": captured_at,
                "source": "Groww historical contracts API",
            })
    if not rows:
        raise RuntimeError("Groww returned no contracts for the selected underlying/year/month.")

    output = Path(args.output) if args.output else (
        REPOSITORY_ROOT / "data" / "cache" / "instruments"
        / f"groww_contracts_{args.underlying.upper()}_{args.year}"
        f"{f'_{args.month:02d}' if args.month else ''}.csv"
    )
    if not output.is_absolute():
        output = REPOSITORY_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).drop_duplicates(
        subset=["exchange", "segment", "underlying", "expiry", "contract_symbol"]
    ).sort_values(["expiry", "contract_symbol"]).to_csv(output, index=False)
    print(f"Saved {len(rows)} contract rows to {output}")
    print("Note: lot size, tick size, margins, and settlement rules are not provided by this snapshot.")


if __name__ == "__main__":
    main()
