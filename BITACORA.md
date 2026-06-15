# BITACORA — market-data-mcp

---

## 2026-06-14 — Sesion 1 — v0.1 construido (tercer output de mcp-factory)

**Que es:** MCP server de datos de mercado en tiempo real para agentes IA.
6 tools sobre Finnhub free tier + Alpaca paper (opcional). Pieza de portfolio
para Upwork (build-once, sell-many). Generado con mcp-factory.

**Completado:**
- Generated with `python new_server.py market-data-mcp "..."` from factory
- 5 sources built under `market_data_mcp/sources/`:
  - `quote.py` — real-time price via Finnhub /quote (TTL 60s)
  - `news.py` — company-specific (last 7 days) + general market headlines (TTL 5min)
  - `calendar.py` — earnings calendar /calendar/earnings (TTL 30min)
  - `scan.py` — multi-ticker watchlist scanner, sorted by |change_pct| (TTL 60s)
  - `broker.py` — Alpaca paper positions, optional/cabled-off without keys
- `analyze.py` composite: quote (momentum score) + news (catalyst) + calendar (earnings flag)
- `server.py`: 6 tools registered (market_quote, market_news, market_calendar, market_scan, market_analyze, broker_positions)
- Example source/tool from template deleted
- `tests/test_smoke.py` rewritten: 8 live checks including graceful degradation cases
- `evals/market_data_eval.xml`: 8 deterministic Q/A pairs
- README rewritten with live demo output, Claude Desktop config, tool table

**Live test results (2026-06-14, market open):**
- market_quote AAPL: $291.13 (-1.52%) — LIVE
- market_news AAPL: 5 headlines from Yahoo/Reuters — LIVE
- market_news general: 5 Reuters headlines (US-Iran deal) — LIVE
- market_calendar 7 days: 20 events (ACN, KR, MEI...) — LIVE (FREE TIER, not premium-gated)
- market_scan AAPL,MSFT,NVDA,TSLA: Top mover TSLA +1.82% — LIVE
- market_analyze AAPL: -30/100 Lean negative [TRIM], confidence 60% — LIVE
- broker_positions (no keys): graceful "keys not set" degradation — PASS

**Key findings:**
- /calendar/earnings is accessible on Finnhub free tier (no 403 as of this date)
- Finnhub returns c=0 for unknown symbols (not an error HTTP code) — handled in quote.py
- No separate Alpaca keys available; broker is cabled-but-off by design (documented hook)

**Decisions:**
- Score scale: +-5% intraday = +-100 (appropriate for stocks; crypto uses different scale)
- News: top 5 headlines, no NLP sentiment (would require a paid model or separate API)
- Calendar: TTL 30min (infrequent changes), capped at 20 events to keep response readable
- Scan: sorted by abs(change_pct) desc — "movers" angle is the product differentiator

**Factory lesson:** third server from this factory. The pattern (generate -> delete example -> build sources -> wire server -> test) is now internalized. Each server takes ~2-3 hours of focused work.

**Pendiente (Fase 6 — acciones humanas):**
- [ ] Claude Desktop: paste mcpServers block from README, restart, test live
- [ ] Video demo 60s -> portfolio Upwork/Lemon.io
- [ ] GitHub publico + topics `mcp` `claude` `finnhub` `market-data` `model-context-protocol`
