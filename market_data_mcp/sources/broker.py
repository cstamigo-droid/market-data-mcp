"""Broker positions — Alpaca paper trading (optional, cabled-but-off by default).

Reads open positions from Alpaca Paper Trading API. If ALPACA_API_KEY /
ALPACA_SECRET_KEY are absent, degrades gracefully with Result.failed — this
is a documented optional hook, not a required source.

Get paper keys at: https://app.alpaca.markets/ → Paper Trading → API Keys
"""
from __future__ import annotations

import os

import requests

from .. import cache
from ..result import Result

_URL = "https://paper-api.alpaca.markets/v2/positions"
_TTL_S = 30.0  # positions can change, keep cache short


def _pull(api_key: str, secret_key: str) -> list[dict]:
    resp = requests.get(
        _URL,
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def fetch() -> Result:
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    if not api_key or not secret_key:
        return Result.failed(
            "broker",
            "ALPACA_API_KEY / ALPACA_SECRET_KEY not set — optional source, see README",
        )

    try:
        positions = cache.get_or_fetch(
            "alpaca_positions", _TTL_S, lambda: _pull(api_key, secret_key)
        )
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        return Result.failed("broker", f"Alpaca API error HTTP {status}: {e}")
    except Exception as e:
        return Result.failed("broker", str(e))

    if not positions:
        return Result(
            source="broker",
            ok=True,
            summary="Alpaca paper account: no open positions.",
            data={"count": 0, "positions": [], "url": "https://app.alpaca.markets/"},
        )

    items = [
        {
            "symbol": p.get("symbol"),
            "qty": p.get("qty"),
            "side": p.get("side"),
            "avg_entry_price": p.get("avg_entry_price"),
            "current_price": p.get("current_price"),
            "unrealized_pl": p.get("unrealized_pl"),
            "unrealized_plpc": p.get("unrealized_plpc"),
        }
        for p in positions
    ]

    total_pl = sum(
        float(p.get("unrealized_pl") or 0) for p in positions
    )
    direction = "+" if total_pl >= 0 else ""
    summary = (
        f"Alpaca paper: {len(items)} open position(s). "
        f"Total unrealized P&L: {direction}${total_pl:,.2f}"
    )
    return Result(
        source="broker",
        ok=True,
        summary=summary,
        data={
            "count": len(items),
            "total_unrealized_pl": round(total_pl, 2),
            "positions": items,
            "url": "https://app.alpaca.markets/",
        },
    )
