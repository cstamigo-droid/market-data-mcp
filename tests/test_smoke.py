"""Smoke test — hits ALL real data sources and prints each Result with ok/failed status.

Run:  PYTHONUTF8=1 python tests/test_smoke.py
This is a LIVE network test (not a unit test). Every source must return real data
or degrade gracefully with Result.failed — never fabricated values.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from market_data_mcp import cache  # noqa: E402
from market_data_mcp.analyze import analyze  # noqa: E402
from market_data_mcp.formatting import ResponseFormat, render  # noqa: E402
from market_data_mcp.sources import broker, calendar, news, quote, scan  # noqa: E402

SEP = "=" * 70
PASS = "[ok=True ]"
FAIL = "[ok=False]"


def _status(result) -> str:
    tag = PASS if result.ok else FAIL
    score_s = f"  score={result.score:+.1f}" if result.score is not None else ""
    conf_s = f"  confidence={result.confidence:.2f}" if result.confidence is not None else ""
    err_s = f"  error={result.error!r}" if not result.ok else ""
    return f"{tag}{score_s}{conf_s}{err_s}"


def run(label: str, result, title: str) -> bool:
    print(f"\n{SEP}\n  {label}\n{SEP}")
    print(render(result, title, ResponseFormat.MARKDOWN))
    print(_status(result))
    return result.ok


def main() -> None:
    cache.clear()
    results: list[tuple[str, bool]] = []

    # ── 1. Quote: AAPL (should work) ──────────────────────────────────────────
    r = quote.fetch("AAPL")
    ok = run("QUOTE — AAPL (should return live price)", r, "Quote — AAPL")
    results.append(("quote AAPL", ok))

    # ── 2. Quote: unknown symbol (should degrade, not crash) ──────────────────
    cache.clear()
    r2 = quote.fetch("XXXX_FAKE_TICKER_9999")
    ok2 = not r2.ok  # expected to FAIL gracefully (ok=False is the right behavior)
    print(f"\n{SEP}\n  QUOTE — unknown symbol (expected graceful degradation)\n{SEP}")
    print(render(r2, "Quote — XXXX_FAKE_TICKER_9999", ResponseFormat.MARKDOWN))
    print(_status(r2))
    print(f"  Graceful degradation: {'PASS' if ok2 else 'FAIL (got ok=True on unknown ticker!)'}")
    results.append(("quote unknown-symbol graceful", ok2))

    # ── 3. News: AAPL company news ────────────────────────────────────────────
    r = news.fetch("AAPL")
    ok = run("NEWS — AAPL company news", r, "News — AAPL")
    results.append(("news AAPL", ok))

    # ── 4. News: general (no symbol) ──────────────────────────────────────────
    r = news.fetch(None)
    ok = run("NEWS — general market (no symbol)", r, "General Market News")
    results.append(("news general", ok))

    # ── 5. Calendar (may be premium-gated) ────────────────────────────────────
    r = calendar.fetch(days=7)
    ok = run("CALENDAR — next 7 days (may be premium-gated)", r, "Earnings Calendar")
    results.append(("calendar", ok))

    # ── 6. Scan: multi-ticker ─────────────────────────────────────────────────
    r = scan.fetch("AAPL,MSFT,NVDA,TSLA")
    ok = run("SCAN — AAPL,MSFT,NVDA,TSLA", r, "Watchlist Scan")
    results.append(("scan 4 tickers", ok))

    # ── 7. Analyze: composite ─────────────────────────────────────────────────
    r = analyze("AAPL")
    ok = run("ANALYZE — AAPL composite", r, "Analysis — AAPL")
    results.append(("analyze AAPL", ok))

    # ── 8. Broker: no keys (should degrade, not crash) ────────────────────────
    r = broker.fetch()
    print(f"\n{SEP}\n  BROKER — no Alpaca keys (expected graceful degradation)\n{SEP}")
    print(render(r, "Broker Positions", ResponseFormat.MARKDOWN))
    print(_status(r))
    ok8 = not r.ok  # expected to FAIL gracefully (keys not set)
    print(f"  Graceful degradation: {'PASS' if ok8 else 'FAIL (got ok=True without keys!)'}")
    results.append(("broker no-keys graceful", ok8))

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SUMMARY")
    print(SEP)
    all_pass = True
    for label, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status}  {label}")
        if not passed:
            all_pass = False
    print(SEP)
    print(f"  {'ALL PASS' if all_pass else 'SOME FAILURES — see above'}")
    print(SEP)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
