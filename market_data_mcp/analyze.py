"""Composite market analysis — combines quote + news + calendar into one verdict.

Builds a momentum-flavored score from the live quote's % change, then layers in
the nearest news headline as a catalyst signal and earnings proximity as a risk
flag. Each component degrades gracefully: if quote fails nothing is fabricated.

Score logic (-100..+100):
  - Base from change_pct: scaled such that ±5% → ±100 (intraday swing scale).
  - News: presence of news bumps confidence slightly (we can't score sentiment
    without an NLP model, so we don't pretend to).
  - Earnings proximity: if earnings < 3 days away, note it in the narrative.
"""
from __future__ import annotations

from .result import Result, clamp
from .sources import calendar, news, quote


def _momentum_score(change_pct: float) -> float:
    """Scale intraday % change to -100..+100. ±5% maps to ±100."""
    return clamp(change_pct / 5.0 * 100.0, -100.0, 100.0)


def _verdict(score: float) -> tuple[str, str]:
    if score >= 40:
        return "Strong momentum", "LONG BIAS"
    if score >= 15:
        return "Lean positive", "ACCUMULATE"
    if score > -15:
        return "Neutral / consolidating", "WATCH"
    if score > -40:
        return "Lean negative", "TRIM"
    return "Strong selling pressure", "AVOID / SHORT BIAS"


def analyze(symbol: str) -> Result:
    """Fan out to quote + news + calendar, then synthesize a narrative verdict."""
    t = symbol.upper().strip()

    q = quote.fetch(t)
    n = news.fetch(t)
    cal = calendar.fetch(days=7)

    # ── quote is the backbone — without it we can't score ──
    if not q.ok:
        return Result.failed(
            "analyze",
            f"quote unavailable for {t}: {q.error}",
        )

    change_pct = q.data.get("change_pct", 0.0) or 0.0
    price = q.data.get("price", 0.0)
    score = _momentum_score(change_pct)
    confidence = 0.5  # base confidence from a single data point

    # ── news: presence boosts confidence a bit ──
    latest_headline = None
    if n.ok and n.data.get("articles"):
        latest_headline = n.data["articles"][0].get("headline", "")
        confidence = min(confidence + 0.1, 0.8)

    # ── earnings proximity: flag but don't inflate score ──
    earnings_note = ""
    if cal.ok and cal.data.get("events"):
        upcoming = [
            e for e in cal.data["events"] if e.get("symbol", "").upper() == t
        ]
        if upcoming:
            next_date = upcoming[0].get("date", "")
            earnings_note = f" | EARNINGS {next_date} (expect volatility)"
            confidence = min(confidence + 0.05, 0.85)

    verdict, action = _verdict(score)
    direction = "+" if change_pct >= 0 else ""
    summary = (
        f"{t}: ${price:,.2f}  {direction}{change_pct:.2f}%  →  {verdict}  [{action}]"
        + (f"  | Catalyst: {latest_headline[:100]}" if latest_headline else "")
        + earnings_note
    )

    # Collect data from sub-results for traceability
    data: dict = {
        "symbol": t,
        "price": price,
        "change_pct": change_pct,
        "verdict": verdict,
        "action": action,
        "sources_ok": {
            "quote": q.ok,
            "news": n.ok,
            "calendar": cal.ok,
        },
        "url": f"https://finnhub.io/",
    }
    if latest_headline:
        data["latest_headline"] = latest_headline
    if earnings_note:
        data["earnings_note"] = earnings_note.strip(" |")

    return Result(
        source="analyze",
        ok=True,
        score=round(score, 1),
        confidence=round(confidence, 2),
        summary=summary,
        data=data,
    )
