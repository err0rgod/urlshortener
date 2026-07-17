import os
from html import escape
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import create_engine, text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

DB_PATH = os.getenv("DB_PATH")
if not DB_PATH:
    raise RuntimeError("DB_PATH is not set.")

engine = create_engine(DB_PATH, pool_pre_ping=True)
app = FastAPI(title="FlexURL Badge Counters")

COUNTER_ALIASES = {
    "links": "links_created",
    "links-created": "links_created",
    "links_created": "links_created",
    "visits": "visitors",
    "visitors": "visitors",
}

DEFAULT_LABELS = {
    "links_created": "links created",
    "visitors": "visitors",
}


def normalize_counter(counter: str) -> str:
    normalized = COUNTER_ALIASES.get(counter.strip().lower())
    if not normalized:
        raise HTTPException(status_code=404, detail="Unknown badge counter")
    return normalized


def get_counter_value(counter: str) -> int:
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT value FROM public.badge_counters WHERE name = :name"),
            {"name": counter},
        ).scalar_one_or_none()
    return int(value or 0)


def compact_number(value: int) -> str:
    for suffix, divisor in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if value >= divisor:
            compact = value / divisor
            return f"{compact:.1f}{suffix}" if compact < 10 else f"{compact:.0f}{suffix}"
    return str(value)


def clean_color(value: str, fallback: str) -> str:
    allowed = "0123456789abcdefABCDEF"
    color = value.strip().lstrip("#")
    if len(color) in (3, 6) and all(char in allowed for char in color):
        return f"#{color}"
    named = {
        "black": "#111827",
        "green": "#16a34a",
        "blue": "#2563eb",
        "red": "#dc2626",
        "gray": "#64748b",
        "slate": "#334155",
        "orange": "#ea580c",
        "purple": "#7c3aed",
    }
    return named.get(value.strip().lower(), fallback)


def text_width(text: str) -> int:
    return max(36, len(text) * 7 + 18)


def render_badge(label: str, value: str, left_color: str, right_color: str) -> str:
    label_width = text_width(label)
    value_width = text_width(value)
    total_width = label_width + value_width
    escaped_label = escape(label)
    escaped_value = escape(value)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{escaped_label}: {escaped_value}">
  <title>{escaped_label}: {escaped_value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="{left_color}"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{right_color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{label_width * 5}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(label_width - 10) * 10}">{escaped_label}</text>
    <text x="{label_width * 5}" y="140" transform="scale(.1)" fill="#fff" textLength="{(label_width - 10) * 10}">{escaped_label}</text>
    <text aria-hidden="true" x="{(label_width + value_width / 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(value_width - 10) * 10}">{escaped_value}</text>
    <text x="{(label_width + value_width / 2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(value_width - 10) * 10}">{escaped_value}</text>
  </g>
</svg>
"""


@app.get("/badge/{counter}.svg")
async def badge(
    counter: str,
    left_text: Optional[str] = Query(default=None, max_length=40),
    left_color: str = Query(default="black", max_length=20),
    right_color: str = Query(default="green", max_length=20),
    units: str = Query(default="compact", pattern="^(compact|raw)$"),
):
    counter_name = normalize_counter(counter)
    count = get_counter_value(counter_name)
    label = (left_text or DEFAULT_LABELS[counter_name]).strip()
    value = compact_number(count) if units == "compact" else str(count)
    svg = render_badge(
        label=label,
        value=value,
        left_color=clean_color(left_color, "#111827"),
        right_color=clean_color(right_color, "#16a34a"),
    )
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/health")
async def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
