# -*- coding: utf-8 -*-
"""
Resolve a place name to latitude/longitude and the correct IANA timezone.

- lat/lon -> timezone: offline via `timezonefinder` (bundled polygon data).
- place name -> lat/lon: online via OpenStreetMap Nominatim (free, no API key).
  Nominatim asks for a descriptive User-Agent and ~1 req/sec; we honour both.

The IANA timezone plus Python's zoneinfo gives the *historically correct* UTC
offset for the birth date (e.g. Kyiv on 1988-06-26 was UTC+4 under Soviet
summer time) — no manual per-era tables needed.
"""
from __future__ import annotations
from functools import lru_cache
from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()

@lru_cache(maxsize=1)
def _geocoder():
    from geopy.geocoders import Nominatim
    return Nominatim(user_agent="jyotish-almanac/1.0")

def tz_for(lat: float, lon: float) -> str:
    tz = _tf.timezone_at(lat=lat, lng=lon)
    return tz or "UTC"

def resolve_place(place: str) -> dict:
    """place -> {'lat','lon','tz','label'}. Raises ValueError if not found."""
    loc = _geocoder().geocode(place, language="en", timeout=10)
    if not loc:
        raise ValueError(f"Место не найдено: {place!r}. Попробуйте уточнить или введите координаты вручную.")
    lat, lon = float(loc.latitude), float(loc.longitude)
    return {"lat": lat, "lon": lon, "tz": tz_for(lat, lon), "label": loc.address}

def resolve(place: str | None, lat: float | None, lon: float | None, tz: str | None) -> dict:
    """Flexible entry: prefer explicit lat/lon(+tz), else geocode the place name."""
    if lat is not None and lon is not None:
        return {"lat": float(lat), "lon": float(lon),
                "tz": tz or tz_for(float(lat), float(lon)),
                "label": place or f"{lat:.4f}, {lon:.4f}"}
    if not place:
        raise ValueError("Укажите либо место рождения, либо координаты (широта/долгота).")
    return resolve_place(place)
