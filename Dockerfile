# market-data-mcp — MCP server (stdio transport).
# Cumple el requisito de Glama: la imagen arranca el server y responde a introspección.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY market_data_mcp ./market_data_mcp

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps .

# El server habla por stdio (Claude Desktop / Claude Code / introspección de Glama).
ENTRYPOINT ["market-data-mcp"]
