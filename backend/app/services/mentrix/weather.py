"""Mentrix weather_report — Open-Meteo geocode + forecast (no API key)."""

from __future__ import annotations

from typing import Any

import httpx

# WMO weather interpretation codes (subset)
_WMO = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "rain",
    65: "heavy rain",
    71: "slight snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


def _condition(code: int | None) -> str:
    if code is None:
        return "unknown"
    return _WMO.get(int(code), f"code {code}")


def weather_report(location: str = "") -> dict[str, Any]:
    """Fetch current weather + short forecast for a place name or lat,lon."""
    loc = (location or "").strip() or "Austin"
    try:
        with httpx.Client(timeout=8.0) as client:
            # lat,lon shortcut
            if "," in loc and all(p.strip().replace(".", "", 1).replace("-", "", 1).isdigit() for p in loc.split(",", 1)):
                parts = [p.strip() for p in loc.split(",", 1)]
                lat, lon = float(parts[0]), float(parts[1])
                place = f"{lat:.2f},{lon:.2f}"
                country = ""
            else:
                geo = client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": loc, "count": 1, "language": "en", "format": "json"},
                )
                geo.raise_for_status()
                results = (geo.json() or {}).get("results") or []
                if not results:
                    return {
                        "ok": False,
                        "error": "location_not_found",
                        "location": loc,
                        "spoken_summary": f"I could not find weather for {loc}. Try a city name.",
                    }
                r0 = results[0]
                lat = float(r0["latitude"])
                lon = float(r0["longitude"])
                place = r0.get("name") or loc
                country = r0.get("country_code") or r0.get("country") or ""

            fc = client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "hourly": "temperature_2m,weather_code",
                    "forecast_hours": 6,
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "timezone": "auto",
                },
            )
            fc.raise_for_status()
            data = fc.json() or {}
            cur = data.get("current") or {}
            temp = cur.get("temperature_2m")
            humidity = cur.get("relative_humidity_2m")
            wind = cur.get("wind_speed_10m")
            code = cur.get("weather_code")
            cond = _condition(code if code is not None else None)
            hourly = data.get("hourly") or {}
            hours: list[dict[str, Any]] = []
            temps = hourly.get("temperature_2m") or []
            codes = hourly.get("weather_code") or []
            times = hourly.get("time") or []
            for i in range(min(6, len(temps))):
                hours.append(
                    {
                        "time": times[i] if i < len(times) else "",
                        "temp_f": temps[i],
                        "conditions": _condition(codes[i] if i < len(codes) else None),
                    }
                )
            label = f"{place}" + (f", {country}" if country else "")
            spoken = (
                f"In {label} it is {temp} degrees Fahrenheit and {cond}. "
                f"Humidity {humidity} percent, wind {wind} miles per hour."
            )
            md_lines = [
                f"# Weather — {label}",
                "",
                f"**Now:** {temp}°F, {cond}",
                f"**Humidity:** {humidity}% · **Wind:** {wind} mph",
                "",
                "## Next hours",
            ]
            for h in hours[:6]:
                md_lines.append(f"- {h.get('time', '')}: {h.get('temp_f')}°F, {h.get('conditions')}")
            return {
                "ok": True,
                "location": label,
                "latitude": lat,
                "longitude": lon,
                "temperature_f": temp,
                "humidity": humidity,
                "wind_mph": wind,
                "conditions": cond,
                "hourly": hours,
                "spoken_summary": spoken,
                "board": {
                    "type": "markdown",
                    "title": f"Weather — {label}",
                    "body": "\n".join(md_lines),
                },
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "location": loc,
            "spoken_summary": f"Weather lookup failed for {loc}. I can try Mentrix research instead.",
            "fallback_research": True,
        }
