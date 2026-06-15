"""Real-time stock quote from Finnhub (/quote, free tier).

Returns current price, change, % change, day high/low, open, and previous close.
Finnhub returns zeros for unknown symbols — treated as no-data, not a real quote.
Needs FINNHUB_API_KEY.
"""
from __future__ import annotations

import os

import requests

from .. import cache
from ..result import Result

_URL = "https://finnhub.io/api/v1/quote"
_TTL_S = 60.0  # quotes age fast


def _pull(symbol: str, key: str) -> dict:
    resp = requests.get(
        _URL,
        params={"symbol": symbol, "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def fetch(symbol: str) -> Result:
    t = symbol.upper().strip()
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        return Result.failed("quote", "FINNHUB_API_KEY not set")
    try:
        d = cache.get_or_fetch(f"fh_quote:{t}", _TTL_S, lambda: _pull(t, key))
    except Exception as e:
        return Result.failed("quote", str(e))

    current = d.get("c")
    # Finnhub returns 0 for unknown/delisted symbols — treat as no data
    if not current:
        return Result.failed("quote", f"no price data for {t} (unknown symbol or market closed)")

    change = d.get("d", 0.0) or 0.0
    change_pct = d.get("dp", 0.0) or 0.0
    direction = "+" if change >= 0 else ""
    summary = (
        f"{t}: ${current:,.2f}  ({direction}{change_pct:.2f}%  {direction}${change:.2f})  "
        f"prev close ${d.get('pc', 0):,.2f}"
    )
    return Result(
        source="quote",
        ok=True,
        summary=summary,
        data={
            "symbol": t,
            "price": round(current, 4),
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "high": d.get("h"),
            "low": d.get("l"),
            "open": d.get("o"),
            "prev_close": d.get("pc"),
            "url": f"https://finnhub.io/",
        },
    )
