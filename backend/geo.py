# -*- coding: utf-8 -*-
"""
Resolve a place name to latitude/longitude and the correct IANA timezone.

Resolution order:
  1. explicit lat/lon from the user            -> used directly
  2. offline worldwide city database (geonamescache, ~32k cities incl.
     non-Latin alternate names)                -> instant, no network
  3. OpenStreetMap Nominatim (online)          -> long-tail fallback

Name collisions are broken by population (so "Moscow" -> Russia, not Idaho),
and an optional ", Country" hint disambiguates further ("Moscow, USA").
lat/lon -> timezone is offline via timezonefinder; the IANA zone + zoneinfo
give the historically correct UTC offset for the birth date.

Nothing here crashes the request: unresolved places raise ValueError, which the
API returns as a readable 400 (never a 500).
"""
from __future__ import annotations
from functools import lru_cache
from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()

# ---- small country-name -> ISO2 aliases (Russian + common English) ----
_COUNTRY_ALIASES = {
    "россия":"RU","russia":"RU","рф":"RU",
    "украина":"UA","ukraine":"UA",
    "беларусь":"BY","белоруссия":"BY","belarus":"BY",
    "казахстан":"KZ","kazakhstan":"KZ",
    "узбекистан":"UZ","uzbekistan":"UZ",
    "сша":"US","usa":"US","united states":"US","america":"US",
    "великобритания":"GB","англия":"GB","uk":"GB","united kingdom":"GB","england":"GB",
    "германия":"DE","germany":"DE","франция":"FR","france":"FR",
    "италия":"IT","italy":"IT","испания":"ES","spain":"ES",
    "польша":"PL","poland":"PL","канада":"CA","canada":"CA",
    "израиль":"IL","israel":"IL","грузия":"GE","georgia":"GE",
    "армения":"AM","armenia":"AM","азербайджан":"AZ","azerbaijan":"AZ",
    "молдова":"MD","moldova":"MD","латвия":"LV","latvia":"LV",
    "литва":"LT","lithuania":"LT","эстония":"EE","estonia":"EE",
}

def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())

@lru_cache(maxsize=1)
def _index():
    """Build {normalized_name -> [(pop, lat, lon, countrycode), ...]} once."""
    import geonamescache
    gc = geonamescache.GeonamesCache()
    idx: dict[str, list] = {}
    # country name -> iso, from the built-in country table
    countries = gc.get_countries()
    cname_to_iso = {}
    for iso, c in countries.items():
        cname_to_iso[_norm(c["name"])] = iso
    cname_to_iso.update(_COUNTRY_ALIASES)

    for c in gc.get_cities().values():
        try:
            pop = int(c.get("population") or 0)
            lat = float(c["latitude"]); lon = float(c["longitude"])
            cc = c.get("countrycode", "")
        except Exception:
            continue
        names = [c.get("name", "")] + list(c.get("alternatenames", []) or [])
        for nm in names:
            key = _norm(nm)
            if not key:
                continue
            idx.setdefault(key, []).append((pop, lat, lon, cc))
    # keep the strongest few candidates per name (by population)
    for k in idx:
        idx[k] = sorted(idx[k], key=lambda t: -t[0])[:6]
    return idx, cname_to_iso

@lru_cache(maxsize=1)
def _geocoder():
    from geopy.geocoders import Nominatim
    return Nominatim(user_agent="jyotish-almanac/1.0")

def tz_for(lat: float, lon: float) -> str:
    return _tf.timezone_at(lat=lat, lng=lon) or "UTC"

def resolve_place(place: str) -> dict:
    """place -> {'lat','lon','tz','label'}. Offline DB first, then Nominatim."""
    idx, cname_to_iso = _index()
    parts = [p.strip() for p in place.split(",") if p.strip()]
    city = _norm(parts[0]) if parts else ""
    country_hint = None
    if len(parts) > 1:
        country_hint = cname_to_iso.get(_norm(parts[-1]))

    cands = idx.get(city)
    if cands:
        chosen = None
        if country_hint:
            chosen = next((t for t in cands if t[3] == country_hint), None)
        if chosen is None:
            chosen = cands[0]                      # highest population
        _, lat, lon, _cc = chosen
        return {"lat": lat, "lon": lon, "tz": tz_for(lat, lon), "label": place}

    # online fallback — never allowed to crash the request
    try:
        loc = _geocoder().geocode(place, language="en", timeout=8)
    except Exception:
        raise ValueError(
            f"Не удалось определить координаты для «{place}». "
            "Проверьте написание города или раскройте «Координаты вручную» "
            "и введите широту и долготу."
        )
    if not loc:
        raise ValueError(
            f"Место не найдено: «{place}». Уточните название "
            "или введите координаты вручную."
        )
    lat, lon = float(loc.latitude), float(loc.longitude)
    return {"lat": lat, "lon": lon, "tz": tz_for(lat, lon), "label": loc.address}

def resolve(place, lat, lon, tz):
    """Prefer explicit lat/lon(+tz); else resolve the place name."""
    if lat is not None and lon is not None:
        return {"lat": float(lat), "lon": float(lon),
                "tz": tz or tz_for(float(lat), float(lon)),
                "label": place or f"{lat:.4f}, {lon:.4f}"}
    if not place:
        raise ValueError("Укажите место рождения или координаты (широта/долгота).")
    return resolve_place(place)
