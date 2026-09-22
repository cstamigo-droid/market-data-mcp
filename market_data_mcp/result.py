"""The single return type every source and tool produces.

A uniform shape lets an LLM reason *across* heterogeneous tools without each one
inventing its own format. Plain-data tools fill `summary` + `data`. Analysis
tools additionally set `score` (-100..+100) and `confidence` (0..1), which unlocks
the gauge rendering in `formatting.py`.
"""
from __future__ import annotations

import os
import re

from dataclasses import asdict, dataclass, field
from typing import Any


def clamp(x: float, lo: float, hi: float) -> float:
    """Constrain x to the inclusive [lo, hi] range."""
    return max(lo, min(hi, x))


@dataclass
class Result:
    """Uniform result object returned by every source in `sources/`.

    Attributes:
        source:     short id of the producing source, e.g. "weather".
        ok:         True if data was fetched and the result is meaningful.
        summary:    one-line human-readable takeaway.
        data:       raw structured details (source-specific). Put a `url`
                    permalink here so an agent can cite the source.
        score:      optional -100..+100 directional score (analysis tools only).
        confidence: optional 0..1 — how much to trust this result.
        error:      failure reason when ok is False; None otherwise.
    """

    source: str
    ok: bool
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
    confidence: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def failed(cls, source: str, error: str) -> "Result":
        """Graceful degradation: a missing source NEVER fabricates a value.

        Returns ok=False with no score, so a composite tool can simply skip it
        and the agent sees an honest "no data".
        """
        safe = redact(error)
        return cls(source=source, ok=False, summary=f"no data ({safe})", error=safe)


_SECRET_ENV = ("FINNHUB_API_KEY", "ALPACA_API_KEY", "ALPACA_SECRET_KEY")
_SECRET_QS = re.compile(
    r"((?:token|api[-_]?key|apikey|key|secret)=)[^&\s\'\"]+", re.I
)


def redact(text: object) -> str:
    """Strip credentials out of any text before it reaches the agent.

    Two things used to put the key in front of the model: `requests` embeds the
    request URL in its HTTPError message (the key travelled there as `token=`),
    and urllib3 echoes a header value back when it rejects it -- which happens
    for a key copy-pasted with a trailing newline. Keys now travel in a header
    and are stripped at the source; this stays as a backstop, and covers the
    escaped forms a repr() would produce.
    """
    out = str(text)
    for name in _SECRET_ENV:
        raw = os.getenv(name, "")
        for value in (raw, raw.strip(), repr(raw)[1:-1], repr(raw.strip())[1:-1]):
            if len(value) >= 8:
                out = out.replace(value, "***REDACTED***")
    return _SECRET_QS.sub(r"\1***REDACTED***", out)
