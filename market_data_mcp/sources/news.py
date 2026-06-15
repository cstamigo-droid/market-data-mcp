"""Market news from Finnhub — company-specific or general market news (free tier).

- With symbol: GET /company-news (last 7 days) → top 5 headlines for that ticker.
- Without symbol: GET /news?category=general → top 5 general market headlines.
Needs FINNHUB_API_KEY.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import requests

from .. import cache
from ..result import Result

_BASE = "https://finnhub.io/api/v1"
_TTL_S = 300.0  # 5 min — news doesn't change second by second
_MAX_ITEMS = 5


def _pull_company(symbol: str, key: str) -> list[dict]:
    today = date.today()
    frm = (today - timedelta(days=7)).isoformat()
    to = today.isoformat()
    resp = requests.get(
        f"{_BASE}/company-news",
        params={"symbol": symbol, "from": frm, "to": to, "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json() or []


def _pull_general(key: str) -> list[dict]:
    resp = requests.get(
        f"{_BASE}/news",
        params={"category": "general", "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json() or []


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "unknown"
    try:
        return date.fromtimestamp(ts).isoformat()
    except Exception:
        return str(ts)


def fetch(symbol: str | None = None) -> Result:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        return Result.failed("news", "FINNHUB_API_KEY not set")

    if symbol:
        t = symbol.upper().strip()
        cache_key = f"fh_news:{t}"
        try:
            articles = cache.get_or_fetch(cache_key, _TTL_S, lambda: _pull_company(t, key))
        except Exception as e:
            return Result.failed("news", str(e))
        if not articles:
            return Result.failed("news", f"no news found for {t} in the last 7 days")
        source_label = f"company news for {t}"
    else:
        cache_key = "fh_news:general"
        try:
            articles = cache.get_or_fetch(cache_key, _TTL_S, lambda: _pull_general(key))
        except Exception as e:
            return Result.failed("news", str(e))
        if not articles:
            return Result.failed("news", "no general market news returned")
        source_label = "general market news"

    top = articles[:_MAX_ITEMS]
    items = [
        {
            "headline": a.get("headline", "")[:200],
            "source": a.get("source", ""),
            "date": _fmt_ts(a.get("datetime")),
            "url": a.get("url", ""),
        }
        for a in top
        if a.get("headline")
    ]

    if not items:
        return Result.failed("news", "articles found but no readable headlines")

    summary = f"Top {len(items)} headlines ({source_label}): " + " | ".join(
        i["headline"][:80] for i in items
    )
    return Result(
        source="news",
        ok=True,
        summary=summary,
        data={
            "count": len(items),
            "category": source_label,
            "articles": items,
            "url": "https://finnhub.io/",
        },
    )
