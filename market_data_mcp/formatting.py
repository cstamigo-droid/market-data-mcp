"""Render a Result as Markdown (human, default) or JSON (machine) for MCP output."""
from __future__ import annotations

import json
from enum import Enum

from .result import Result, clamp


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


def label(score: float) -> str:
    """Human label for a -100..+100 directional score."""
    if score >= 40:
        return "Strong positive"
    if score >= 12:
        return "Lean positive"
    if score > -12:
        return "Neutral"
    if score > -40:
        return "Lean negative"
    return "Strong negative"


def _gauge(score: float) -> str:
    """A compact ASCII gauge for a -100..+100 score.

    Negative fills left of center, positive fills right, e.g.
    -100 -> `[########|........]`, +50 -> `[........|####....]`.
    """
    n = 8  # half-width
    s = clamp(score, -100, 100)
    filled = int(round(abs(s) / 100 * n))
    if s < 0:
        left, right = "." * (n - filled) + "#" * filled, "." * n
    elif s > 0:
        left, right = "." * n, "#" * filled + "." * (n - filled)
    else:
        left = right = "." * n
    return f"[{left}|{right}]"


def _fmt_value(v: object) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v[:12]) + (" …" if len(v) > 12 else "")
    return str(v)


def render(result: Result, title: str, fmt: ResponseFormat) -> str:
    """Format a single Result for return to an MCP client."""
    if fmt == ResponseFormat.JSON:
        return json.dumps(result.to_dict(), indent=2, default=str)

    lines = [f"# {title}"]
    if not result.ok:
        lines += ["", f"⚠️ No data available — {result.error}"]
        return "\n".join(lines)

    if result.score is not None:
        conf = f"  · confidence {result.confidence:.0%}" if result.confidence is not None else ""
        lines += [
            "",
            f"**Signal:** {label(result.score)}  "
            f"`{_gauge(result.score)}` {result.score:+.0f}/100{conf}",
        ]
    if result.summary:
        lines += ["", result.summary]

    if result.data:
        lines += ["", "## Details"]
        for k, v in result.data.items():
            if v is None or k == "url":
                continue
            lines.append(f"- **{k.replace('_', ' ')}:** {_fmt_value(v)}")
        url = result.data.get("url")
        if url:
            lines += ["", f"Source: {url}"]

    return "\n".join(lines)
