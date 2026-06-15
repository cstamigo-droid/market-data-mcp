"""Data sources. Each module exposes `fetch(query: str) -> Result`.

Add one module per external API/endpoint. Keep the network call dumb, wrap it in
`cache.get_or_fetch`, and return `Result.failed(...)` on any missing data —
never a fabricated value.
"""
