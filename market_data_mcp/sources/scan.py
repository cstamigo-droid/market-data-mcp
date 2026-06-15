"""Watchlist scanner — ranks a list of tickers by absolute % change (movers).

Calls Finnhub /quote for each symbol and returns them sorted by |change_pct| desc.
Capped at 25 symbols to respect the Finnhub free tier (60 req/min). Skips symbols
that fail or return zero-price (unknown); if ALL fail, returns Result.failed.
Needs FINNHUB_API_KEY.
"""
from __future__ import annotations

import os
from typing import Union

import requests

from .. import cache
from ..result import Result

_URL = "https://finnhub.io/api/v1/quote"
_TTL_S = 60.0  # quotes age fast
_MAX_SYMBOLS = 25


def _pull_one(symbol: str, key: str) -> dict:
    resp = requests.get(
        _URL,
        params={"symbol": symbol, "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_symbols(symbols: Union[list, str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return [s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()]


def fetch(symbols: Union[list, str]) -> Result:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        return Result.failed("scan", "FINNHUB_API_KEY not set")

    tickers = _parse_symbols(symbols)
    if not tickers:
        return Result.failed("scan", "no symbols provided")

    # Cap to respect rate limit
    tickers = tickers[:_MAX_SYMBOLS]

    movers = []
    failed_count = 0
    for t in tickers:
        try:
            d = cache.get_or_fetch(f"fh_quote:{t}", _TTL_S, lambda sym=t: _pull_one(sym, key))
            current = d.get("c")
            if not current:  # 0 or None = unknown symbol
                failed_count += 1
                continue
            change_pct = d.get("dp", 0.0) or 0.0
            movers.append(
                {
                    "symbol": t,
                    "price": round(current, 4),
                    "change_pct": round(change_pct, 4),
                    "change": round(d.get("d", 0.0) or 0.0, 4),
                }
            )
        except Exception:
            failed_count += 1
            continue

    if not movers:
        return Result.failed(
            "scan",
            f"all {len(tickers)} symbols failed or returned no data",
        )

    # Sort by absolute % change descending
    movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    top_mover = movers[0]
    direction = "+" if top_mover["change_pct"] >= 0 else ""
    summary = (
        f"Scanned {len(movers)}/{len(tickers)} symbols"
        + (f" ({failed_count} failed)" if failed_count else "")
        + f". Top mover: {top_mover['symbol']} {direction}{top_mover['change_pct']:.2f}%"
    )
    return Result(
        source="scan",
        ok=True,
        summary=summary,
        data={
            "scanned": len(movers),
            "requested": len(tickers),
            "failed": failed_count,
            "movers": movers,
            "url": "https://finnhub.io/",
        },
    )
