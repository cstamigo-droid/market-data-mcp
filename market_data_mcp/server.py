#!/usr/bin/env python3
"""market-data-mcp — Real-time market data: quotes, news, earnings calendar and a watchlist scanner for AI agents, backed by Finnhub.

Transport: stdio (local — Claude Desktop / Claude Code / agents).

Each tool returns a uniform Result rendered as Markdown (default) or JSON.
Sources fail gracefully: a missing key or premium-gated endpoint returns
"no data", never a fabricated value.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from .analyze import analyze
from .formatting import ResponseFormat, render
from .sources import broker, calendar, news, quote, scan

# Load .env from the project root (parent of this package), if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

mcp = FastMCP("market_data_mcp")


# ─── shared helpers ──────────────────────────────────────────────────────────

async def _run(fn, *args):
    """Run a blocking source function in a thread so the event loop stays free."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args))


# ─── input models ────────────────────────────────────────────────────────────

class SymbolInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    symbol: str = Field(
        ...,
        description="Stock ticker symbol, e.g. 'AAPL', 'MSFT', 'NVDA'.",
        min_length=1,
        max_length=10,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for a human-readable report or 'json' for structured data.",
    )


class NewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    symbol: Optional[str] = Field(
        default=None,
        description="Ticker symbol for company-specific news, e.g. 'TSLA'. Omit for general market news.",
        max_length=10,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for a human-readable report or 'json' for structured data.",
    )


class CalendarInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    days: int = Field(
        default=7,
        description="Number of days ahead to look for earnings events (1-30).",
        ge=1,
        le=30,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for a human-readable report or 'json' for structured data.",
    )


class ScanInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    symbols: str = Field(
        ...,
        description="Comma-separated list of ticker symbols to scan, e.g. 'AAPL,MSFT,NVDA,TSLA'. Max 25.",
        min_length=1,
        max_length=500,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for a human-readable report or 'json' for structured data.",
    )


class FormatInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for a human-readable report or 'json' for structured data.",
    )


# ─── tools ───────────────────────────────────────────────────────────────────

@mcp.tool(
    name="market_quote",
    annotations={
        "title": "Real-Time Stock Quote",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def market_quote(params: SymbolInput) -> str:
    """Get a real-time stock quote: price, % change, day high/low, and previous close.

    Backed by Finnhub free tier. Returns 'no data' for unknown/delisted symbols
    (Finnhub returns zeros for unknowns — we treat that as no data, never fabricate).

    Args:
        params: symbol (str) and response_format ('markdown'|'json').

    Examples:
        - "What is Apple's current stock price?" -> symbol='AAPL'
        - "How much is NVIDIA up today?" -> symbol='NVDA'
        - "Get me a quote for Tesla" -> symbol='TSLA'
    """
    result = await _run(quote.fetch, params.symbol)
    return render(result, f"Quote — {params.symbol.upper()}", params.response_format)


@mcp.tool(
    name="market_news",
    annotations={
        "title": "Market News",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def market_news(params: NewsInput) -> str:
    """Fetch the latest market news — company-specific or general market headlines.

    With a symbol: returns top 5 news items for that ticker from the past 7 days.
    Without a symbol: returns top 5 general market headlines.
    Backed by Finnhub free tier.

    Args:
        params: symbol (optional ticker) and response_format ('markdown'|'json').

    Examples:
        - "What's the latest news about Microsoft?" -> symbol='MSFT'
        - "Give me today's market news" -> (no symbol)
        - "Any news on Amazon this week?" -> symbol='AMZN'
    """
    result = await _run(news.fetch, params.symbol)
    title = f"News — {params.symbol.upper()}" if params.symbol else "General Market News"
    return render(result, title, params.response_format)


@mcp.tool(
    name="market_calendar",
    annotations={
        "title": "Earnings Calendar",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def market_calendar(params: CalendarInput) -> str:
    """Fetch the earnings calendar for the next N days.

    Returns upcoming earnings reports with estimated EPS and revenue where available.
    NOTE: This endpoint may be premium-gated on the Finnhub free tier. If so, it
    degrades gracefully with an honest 'no data' message rather than fabricating events.

    Args:
        params: days (int, 1-30, default 7) and response_format.

    Examples:
        - "Which companies report earnings this week?" -> days=7
        - "Show me earnings for the next 2 weeks" -> days=14
        - "What's reporting tomorrow?" -> days=1
    """
    result = await _run(calendar.fetch, params.days)
    return render(result, f"Earnings Calendar — next {params.days} days", params.response_format)


@mcp.tool(
    name="market_scan",
    annotations={
        "title": "Watchlist Scanner",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def market_scan(params: ScanInput) -> str:
    """Scan a watchlist of stocks and rank them by absolute % change (biggest movers first).

    Accepts up to 25 symbols. Unknown or delisted tickers are skipped gracefully.
    Useful for monitoring a portfolio or sector basket for unusual activity.

    Args:
        params: symbols (comma-separated string, max 25) and response_format.

    Examples:
        - "Which of AAPL, MSFT, GOOGL, AMZN, META is moving most today?" -> symbols='AAPL,MSFT,GOOGL,AMZN,META'
        - "Scan my tech watchlist: NVDA,AMD,INTC,TSM,AVGO" -> symbols='NVDA,AMD,INTC,TSM,AVGO'
        - "Show biggest movers in AAPL TSLA MSFT today" -> symbols='AAPL,TSLA,MSFT'
    """
    result = await _run(scan.fetch, params.symbols)
    return render(result, f"Watchlist Scan — {params.symbols}", params.response_format)


@mcp.tool(
    name="market_analyze",
    annotations={
        "title": "Composite Market Analysis",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def market_analyze(params: SymbolInput) -> str:
    """Composite market analysis: momentum score, news catalyst, and earnings proximity.

    Combines real-time quote (momentum), latest news headline (catalyst), and
    earnings calendar (risk flag) into a single scored verdict. Each component
    degrades gracefully — if news or calendar are unavailable, only quote is used.
    Score: -100 (strong selling pressure) to +100 (strong upward momentum).

    Args:
        params: symbol (str) and response_format ('markdown'|'json').

    Examples:
        - "Give me a full read on Apple" -> symbol='AAPL'
        - "What's the momentum on NVIDIA right now?" -> symbol='NVDA'
        - "Analyze Tesla for me" -> symbol='TSLA'
    """
    result = await _run(analyze, params.symbol)
    return render(result, f"Analysis — {params.symbol.upper()}", params.response_format)


@mcp.tool(
    name="broker_positions",
    annotations={
        "title": "Broker Positions (Alpaca Paper)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def broker_positions(params: FormatInput) -> str:
    """Read open positions from an Alpaca paper trading account.

    OPTIONAL — requires ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.
    If keys are absent, returns a graceful 'no data' message with setup instructions.
    Read-only: never places orders or moves money.

    Args:
        params: response_format ('markdown'|'json').

    Examples:
        - "What positions do I have open in my paper account?" -> (no ticker needed)
        - "Show me my paper portfolio" -> (no ticker needed)
    """
    result = await _run(broker.fetch)
    return render(result, "Broker Positions — Alpaca Paper", params.response_format)


def main() -> None:
    """Console entrypoint — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
