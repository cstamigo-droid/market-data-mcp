# Publicación en Glama + awesome-mcp-servers — market-data-mcp
> Proceso 2026: **1 server por PR** + **registro en Glama**.

## ✅ Estado (hecho + verificado 2026-07-06)
- **Dockerfile** (`./Dockerfile`, Python 3.11-slim, stdio) · **build OK** · **introspección VERIFICADA: 6 tools**
  (`market_quote`, `market_news`, `market_calendar`, `market_scan`, `market_analyze`, `broker_positions`).
- `glama.json` ya existe (maintainer `cstamigo-droid`). → Cumple el requisito de Glama.

Verificar: `docker build -t market-data-mcp .` y correr el handshake MCP (ver otros GLAMA_PUBLISH del ecosistema).

## 🙋 Cristian
1. Registrar en https://glama.ai/mcp/servers → `github.com/cstamigo-droid/market-data-mcp` → anotar ruta Glama.
2. Abrir UN PR a `awesome-mcp-servers`.

## 📝 PR
**Título:** `Add market-data-mcp (fast market data: quotes, news, calendar, screener)`
**Entrada README:**
```
- [cstamigo-droid/market-data-mcp](https://github.com/cstamigo-droid/market-data-mcp) 🐍 🏠 - Fast market data over MCP: real-time quotes, news, economic calendar, a rule screener, and broker positions — 6 tools.
```
**Badge** (reemplazar `<GLAMA_PATH>`):
```
[![market-data-mcp MCP server](https://glama.ai/mcp/servers/<GLAMA_PATH>/badges/score.svg)](https://glama.ai/mcp/servers/<GLAMA_PATH>)
```
