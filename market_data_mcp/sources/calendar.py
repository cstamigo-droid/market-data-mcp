"""Earnings calendar from Finnhub (/calendar/earnings, free tier — may be premium-gated).

Returns upcoming earnings reports for the next N days. If the endpoint returns
403 or an access-denied payload, degrades gracefully with Result.failed so the
rest of the server stays functional.
Needs FINNHUB_API_KEY.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import requests

from .. import cache
from ..result import Result

_URL = "https://finnhub.io/api/v1/calendar/earnings"
_TTL_S = 1800.0  # 30 min — calendar changes infrequently


def _pull(frm: str, to: str, key: str) -> dict:
    resp = requests.get(
        _URL,
        params={"from": frm, "to": to, "token": key},
        timeout=10,
    )
    # 403 = premium-gated, raise so we catch it above
    resp.raise_for_status()
    return resp.json()


def fetch(days: int = 7) -> Result:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        return Result.failed("calendar", "FINNHUB_API_KEY not set")

    today = date.today()
    frm = today.isoformat()
    to = (today + timedelta(days=max(1, days))).isoformat()
    cache_key = f"fh_cal:{frm}:{to}"

    try:
        raw = cache.get_or_fetch(cache_key, _TTL_S, lambda: _pull(frm, to, key))
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status == 403:
            return Result.failed(
                "calendar",
                "earnings calendar is premium-gated on the free Finnhub tier (HTTP 403). "
                "Upgrade to a paid plan or swap this source.",
            )
        return Result.failed("calendar", f"HTTP {status}: {e}")
    except Exception as e:
        return Result.failed("calendar", str(e))

    # Finnhub may return {"earningsCalendar": null} or {"earningsCalendar": [...]}
    earnings_list = raw.get("earningsCalendar") if isinstance(raw, dict) else None
    if not earnings_list:
        # Check for access-denied message in body
        if isinstance(raw, dict) and raw.get("error"):
            return Result.failed("calendar", f"API error: {raw['error']}")
        return Result.failed("calendar", f"no earnings events in the next {days} days")

    events = [
        {
            "symbol": e.get("symbol", ""),
            "date": e.get("date", ""),
            "hour": e.get("hour", ""),  # "bmo" before market, "amc" after market
            "eps_estimate": e.get("epsEstimate"),
            "revenue_estimate": e.get("revenueEstimate"),
        }
        for e in earnings_list[:20]  # cap at 20 to keep response readable
        if e.get("symbol")
    ]

    if not events:
        return Result.failed("calendar", "no reportable earnings events found")

    tickers = [e["symbol"] for e in events[:5]]
    summary = f"{len(events)} earnings events in the next {days} days: {', '.join(tickers)}" + (
        " …" if len(events) > 5 else ""
    )
    return Result(
        source="calendar",
        ok=True,
        summary=summary,
        data={
            "period_days": days,
            "from": frm,
            "to": to,
            "count": len(events),
            "events": events,
            "url": "https://finnhub.io/",
        },
    )
