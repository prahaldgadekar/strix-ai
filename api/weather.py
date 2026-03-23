"""
api/weather.py — STRIX v3.0
Uses OpenWeatherMap free API.
Add to .env:  WEATHER_API_KEY=your_key
Get free key: https://openweathermap.org/api (free tier)

Falls back to wttr.in if no API key (no key needed).
"""

import os, time, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY   = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL  = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "pune")   # change to your city

_cache = {}
CACHE_SECONDS = 600  # 10 minutes


def get_weather(city: str = None) -> dict:
    city = city or DEFAULT_CITY
    now  = time.time()

    # Return cached if fresh
    if city in _cache and now - _cache[city]["ts"] < CACHE_SECONDS:
        print(f"[Weather] Cached: {city}")
        return _cache[city]["data"]

    # ── Try OpenWeatherMap if key exists ──────────────────
    if API_KEY:
        try:
            r = requests.get(BASE_URL, params={
                "q":     city,
                "appid": API_KEY,
                "units": "metric",
            }, timeout=8)
            r.raise_for_status()
            d    = r.json()
            data = {
                "city":        d["name"],
                "country":     d["sys"]["country"],
                "temp_c":      round(d["main"]["temp"], 1),
                "feels_like":  round(d["main"]["feels_like"], 1),
                "humidity":    d["main"]["humidity"],
                "description": d["weather"][0]["description"].title(),
                "wind_kmh":    round(d["wind"]["speed"] * 3.6, 1),
                "source":      "OpenWeatherMap",
            }
            _cache[city] = {"ts": now, "data": data}
            return data
        except Exception as e:
            print(f"[Weather] OWM failed: {e} — trying wttr.in")

    # ── Fallback: wttr.in (no key needed) ────────────────
    try:
        r = requests.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=8,
            headers={"User-Agent": "STRIX/1.0"}
        )
        r.raise_for_status()
        d    = r.json()
        cur  = d["current_condition"][0]
        area = d["nearest_area"][0]
        data = {
            "city":        area["areaName"][0]["value"],
            "country":     area["country"][0]["value"],
            "temp_c":      float(cur["temp_C"]),
            "feels_like":  float(cur["FeelsLikeC"]),
            "humidity":    int(cur["humidity"]),
            "description": cur["weatherDesc"][0]["value"],
            "wind_kmh":    float(cur["windspeedKmph"]),
            "source":      "wttr.in",
        }
        _cache[city] = {"ts": now, "data": data}
        return data
    except Exception as e:
        return {"error": f"Weather fetch failed: {e}"}


def format_weather(city: str = None) -> str:
    data = get_weather(city)
    if "error" in data:
        return f"Weather unavailable: {data['error']}"
    return (
        f"Weather in {data['city']}, {data['country']}\n"
        f"  {data['description']}\n"
        f"  Temp     : {data['temp_c']}C  (feels {data['feels_like']}C)\n"
        f"  Humidity : {data['humidity']}%\n"
        f"  Wind     : {data['wind_kmh']} km/h"
    )