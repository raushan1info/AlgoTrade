"""Zerodha Kite Connect historical OHLCV adapter.

This adapter is read-only: it fetches history and instrument metadata but never places orders.
Kite access tokens are short-lived and normally need to be refreshed each trading day.
"""
from datetime import date, datetime, timedelta
import os
from pathlib import Path
from typing import Any

import pandas as pd

from core.base.derivatives import DerivativeContract
from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class KiteConnectMarketDataProvider(MarketDataProvider):
    """Fetch daily historical candles using the official kiteconnect Python SDK."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.api_key_env = self.config.get("api_key_env", "KITE_API_KEY")
        self.access_token_env = self.config.get("access_token_env", "KITE_ACCESS_TOKEN")
        self.instrument_cache_dir = Path(self.config.get("instrument_cache_dir", "data/cache/instruments"))
        self._kite = None

    def _client(self):
        api_key = os.environ.get(self.api_key_env, "").strip()
        access_token = os.environ.get(self.access_token_env, "").strip()
        if not api_key or api_key == "replace_me":
            raise RuntimeError(f"Set {self.api_key_env} in your root .env file.")
        if not access_token or access_token == "replace_me":
            raise RuntimeError(
                f"Set {self.access_token_env} in your root .env file. "
                "Kite access tokens usually expire before the next trading day."
            )
        try:
            from kiteconnect import KiteConnect
        except ImportError as exc:
            raise RuntimeError("Install the optional dependency with pip install -e '.[zerodha]'") from exc
        if self._kite is None:
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            self._kite = kite
        return self._kite

    def _instrument_master(self, exchange: str) -> pd.DataFrame:
        """Return today's cached instrument master for an exchange."""
        exchange = exchange.strip().upper()
        cache_dir = self.instrument_cache_dir
        if not cache_dir.is_absolute():
            cache_dir = Path(__file__).resolve().parents[2] / cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"kite_instruments_{exchange}_{date.today().isoformat()}.csv"
        if cache_file.is_file():
            instruments = pd.read_csv(cache_file)
        else:
            instruments = pd.DataFrame(self._client().instruments(exchange))
            if instruments.empty:
                raise ValueError(f"Kite returned an empty instrument master for {exchange}.")
            temporary = cache_file.with_suffix(".tmp")
            instruments.to_csv(temporary, index=False)
            temporary.replace(cache_file)
        if instruments.empty:
            raise ValueError(f"Kite instrument master is empty for {exchange}.")
        return instruments

    def list_index_instruments(
        self,
        exchanges: tuple[str, ...] = ("NSE", "BSE"),
        prefixes: tuple[str, ...] = ("NIFTY", "SENSEX"),
    ) -> pd.DataFrame:
        """Discover available NIFTY/SENSEX index rows from the provider instrument masters.

        This discovers index instruments, not F&O contracts. Actual historical candle
        availability is tested separately when each index is requested.
        """
        prefix_values = tuple(prefix.upper() for prefix in prefixes)
        discovered: list[pd.DataFrame] = []
        for exchange in exchanges:
            instruments = self._instrument_master(exchange)
            if "tradingsymbol" not in instruments.columns:
                raise ValueError(f"Kite instrument master for {exchange} has no tradingsymbol column")
            symbol = instruments["tradingsymbol"].astype(str).str.upper()
            name = instruments.get(
                "name", pd.Series("", index=instruments.index)
            ).astype(str).str.upper()
            prefix_mask = symbol.map(
                lambda value: any(value.startswith(prefix) for prefix in prefix_values)
            ) | name.map(lambda value: any(value.startswith(prefix) for prefix in prefix_values))
            segment = instruments.get(
                "segment", pd.Series("", index=instruments.index)
            ).astype(str).str.upper()
            instrument_type = instruments.get(
                "instrument_type", pd.Series("", index=instruments.index)
            ).astype(str).str.upper()
            index_mask = segment.isin({"INDICES", "INDEX"}) | instrument_type.eq("INDEX")
            selected = instruments.loc[index_mask & prefix_mask].copy()
            if selected.empty:
                continue
            selected["exchange"] = exchange
            selected["tradingsymbol"] = selected["tradingsymbol"].astype(str)
            selected["instrument_token"] = pd.to_numeric(
                selected["instrument_token"], errors="raise"
            ).astype("int64")
            discovered.append(selected)
        if not discovered:
            raise ValueError(
                "No NIFTY/SENSEX index instruments were found in the selected Kite instrument "
                "masters. Check provider access and the instrument-master schema."
            )
        result = pd.concat(discovered, ignore_index=True)
        result = result.drop_duplicates(subset=["exchange", "instrument_token"])
        return result.sort_values(["exchange", "tradingsymbol"]).reset_index(drop=True)

    def _resolve_token(self, symbol: str) -> int:
        if str(symbol).strip().isdigit():
            return int(symbol)
        if ":" not in symbol:
            raise ValueError(
                "Kite symbols must be an instrument token or EXCHANGE:TRADING_SYMBOL "
                "(for example NSE:RELIANCE)."
            )
        exchange, trading_symbol = (part.strip().upper() for part in symbol.split(":", 1))
        if not exchange or not trading_symbol:
            raise ValueError("Kite symbol must be EXCHANGE:TRADING_SYMBOL.")
        instruments = self._instrument_master(exchange)
        matches = instruments.loc[
            instruments["tradingsymbol"].astype(str).str.upper().eq(trading_symbol)
        ]
        if matches.empty:
            raise ValueError(
                f"Could not resolve {symbol!r} in today's Kite instrument master. "
                "Check exchange/symbol or use the numeric instrument_token."
            )
        if len(matches) > 1:
            raise ValueError(f"Instrument symbol {symbol!r} is ambiguous; use its numeric token.")
        return int(matches.iloc[0]["instrument_token"])


    @staticmethod
    def _normalise_underlying(value: str) -> str:
        aliases = {
            "NIFTY50": "NIFTY",
            "NIFTY": "NIFTY",
            "BANKNIFTY": "BANKNIFTY",
            "BANKNIFTY50": "BANKNIFTY",
            "FINNIFTY": "FINNIFTY",
            "NIFTYFINANCIALSERVICES": "FINNIFTY",
            "MIDCPNIFTY": "MIDCPNIFTY",
            "NIFTYMIDCAPSELECT": "MIDCPNIFTY",
            "SENSEX": "SENSEX",
            "BANKEX": "BANKEX",
        }
        key = "".join(character for character in value.upper() if character.isalnum())
        return aliases.get(key, key)

    def list_derivative_contracts(
        self,
        underlying: str,
        as_of: date,
        exchanges: tuple[str, ...] = ("NFO", "BFO"),
    ) -> list[DerivativeContract]:
        """Discover current/future contracts from the provider's current instrument master.

        This cannot reconstruct expired contracts missing from today's master. Historical
        F&O backtests require archived, point-in-time instrument-master snapshots.
        """
        target = self._normalise_underlying(underlying)
        if not target:
            raise ValueError("underlying must be non-empty")
        contracts: list[DerivativeContract] = []
        for exchange in exchanges:
            master = self._instrument_master(exchange)
            required = {
                "instrument_token", "tradingsymbol", "name", "expiry",
                "instrument_type", "segment", "lot_size", "tick_size",
            }
            missing = required.difference(master.columns)
            if missing:
                raise ValueError(
                    f"Kite {exchange} instrument master is missing columns: {sorted(missing)}"
                )
            underlying_names = master["name"].fillna("").astype(str).map(
                self._normalise_underlying
            )
            expiry_values = pd.to_datetime(master["expiry"], errors="coerce").dt.date
            types = master["instrument_type"].fillna("").astype(str).str.upper()
            segments = master["segment"].fillna("").astype(str).str.upper()
            selected = master.loc[
                underlying_names.eq(target)
                & expiry_values.notna()
                & (expiry_values >= as_of)
                & types.isin({"FUT", "CE", "PE"})
                & segments.str.contains(r"(?:NFO|BFO).*(?:FUT|OPT)|(?:FUT|OPT).*(?:NFO|BFO)", regex=True)
            ]
            for row in selected.to_dict(orient="records"):
                instrument_type = str(row["instrument_type"]).upper()
                expiry_value = pd.Timestamp(row["expiry"]).date()
                strike_value = float(row.get("strike", 0) or 0)
                kind = "future" if instrument_type == "FUT" else "option"
                option_type = None if kind == "future" else instrument_type
                strike = None if kind == "future" else strike_value
                if kind == "option" and strike_value <= 0:
                    continue
                contracts.append(DerivativeContract(
                    instrument_id=str(int(row["instrument_token"])),
                    underlying=target,
                    exchange=exchange,
                    segment=str(row["segment"]),
                    expiry=expiry_value,
                    lot_size=int(row["lot_size"]),
                    tick_size=float(row["tick_size"]),
                    kind=kind,
                    strike=strike,
                    option_type=option_type,
                ))
        return sorted(
            contracts,
            key=lambda contract: (
                contract.expiry,
                contract.kind,
                contract.strike if contract.strike is not None else 0.0,
                contract.option_type or "",
                contract.exchange,
                contract.instrument_id,
            ),
        )

    def get_contract_history(
        self, contract: DerivativeContract, start: str, end: str
    ) -> pd.DataFrame:
        """Fetch history for one exact contract using its instrument token."""
        return self.get_history(contract.instrument_id, start, end)

    @staticmethod
    def _datetime(value: str, *, end: bool = False) -> datetime:
        parsed = datetime.fromisoformat(value)
        if len(value) == 10 and end:
            return parsed.replace(hour=23, minute=59, second=59)
        return parsed

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        start_date = date.fromisoformat(start[:10])
        end_date = date.fromisoformat(end[:10])
        if start_date > end_date:
            raise ValueError("start must be on or before end")
        kite = self._client()
        token = self._resolve_token(symbol)
        records: list[dict[str, Any]] = []
        cursor = start_date
        while cursor <= end_date:
            chunk_end = min(cursor + timedelta(days=364), end_date)
            records.extend(kite.historical_data(
                token,
                self._datetime(cursor.isoformat()),
                self._datetime(chunk_end.isoformat(), end=True),
                self.config.get("kite_interval", "day"),
                continuous=False,
                oi=bool(self.config.get("include_oi", False)),
            ))
            cursor = chunk_end + timedelta(days=1)
        if not records:
            raise ValueError(f"Kite returned no candles for {symbol!r} from {start} through {end}.")
        frame = pd.DataFrame(records).rename(columns={
            "date": "Date", "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        frame = frame.set_index("Date")
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
