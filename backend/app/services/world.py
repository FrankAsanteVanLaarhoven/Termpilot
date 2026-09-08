"""World clock, FX and weather. External APIs are named; failures degrade."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.services import clock

ZONES: list[tuple[str, str]] = [
    ("Europe/London", "London"),
    ("Europe/Paris", "Paris"),
    ("Europe/Berlin", "Berlin"),
    ("America/New_York", "New York"),
    ("America/Sao_Paulo", "São Paulo"),
    ("Africa/Lagos", "Lagos"),
    ("Africa/Nairobi", "Nairobi"),
    ("Asia/Kolkata", "Kolkata"),
    ("Asia/Shanghai", "Shanghai"),
    ("Asia/Tokyo", "Tokyo"),
    ("Asia/Seoul", "Seoul"),
    ("Asia/Manila", "Manila"),
    ("Asia/Karachi", "Karachi"),
    ("Asia/Dhaka", "Dhaka"),
    ("UTC", "UTC"),
]

# Last-resort published snapshot — labelled stale, never mixed with live rates.
_FX_FALLBACK = {
    "GBP": 1.0,
    "EUR": 1.17,
    "USD": 1.27,
    "INR": 106.0,
    "CNY": 9.2,
    "JPY": 190.0,
    "PHP": 74.0,
    "BRL": 7.1,
    "PLN": 5.0,
    "NGN": 1900.0,
}


def world_clock() -> dict[str, Any]:
    now = clock.now()
    items = []
    for zone, label in ZONES:
        local = now.astimezone(ZoneInfo(zone))
        items.append(
            {
                "zone": zone,
                "label": label,
                "time": local.strftime("%H:%M"),
                "date": local.strftime("%a %d %b"),
                "offset": local.strftime("%z"),
            }
        )
    return {"now": now.isoformat(), "items": items}


async def fx_convert(amount: float, base: str, quote: str) -> dict[str, Any]:
    base = base.upper()
    quote = quote.upper()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"https://open.er-api.com/v6/latest/{base}")
        payload = response.json()
        rates = payload.get("rates") or {}
        rate = float(rates[quote])
        return {
            "base": base,
            "quote": quote,
            "rate": rate,
            "amount": amount,
            "converted": round(amount * rate, 4),
            "as_of": payload.get("time_last_update_utc"),
            "source": "open.er-api.com",
            "stale": False,
        }
    except Exception:
        gbp_base = _FX_FALLBACK.get(base)
        gbp_quote = _FX_FALLBACK.get(quote)
        rate = None
        converted = None
        if gbp_base and gbp_quote:
            rate = gbp_quote / gbp_base
            converted = round(amount * rate, 4)
        return {
            "base": base,
            "quote": quote,
            "rate": rate,
            "amount": amount,
            "converted": converted,
            "as_of": None,
            "source": "offline_fixture",
            "stale": True,
        }


async def weather_week(lat: float = 51.5074, lon: float = -0.1278) -> dict[str, Any]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
        "&timezone=Europe%2FLondon"
        "&forecast_days=7"
    )
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    daily = payload.get("daily") or {}
    days = []
    dates = daily.get("time") or []
    for i, date in enumerate(dates):
        parsed = datetime.fromisoformat(date)
        days.append(
            {
                "date": date,
                "label": parsed.strftime("%a"),
                "tmax": daily.get("temperature_2m_max", [None])[i],
                "tmin": daily.get("temperature_2m_min", [None])[i],
                "rain": daily.get("precipitation_probability_max", [None])[i],
                "code": daily.get("weather_code", [None])[i],
            }
        )
    return {
        "place": "London (demo student timezone)",
        "source": "Open-Meteo",
        "days": days,
    }
