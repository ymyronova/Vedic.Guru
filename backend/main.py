# -*- coding: utf-8 -*-
"""
Джйотиш-Альманах — API + static frontend.

Run:  uvicorn main:app --reload --port 8000   (from the backend/ folder)
Then open http://localhost:8000
"""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import geo, jyotish, interpret, render, rectify as rectify_engine, synastry as synastry_engine
import verify

app = FastAPI(title="Jyotish Almanac")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

@app.exception_handler(Exception)
async def any_error(request, exc):
    # Never leak a raw "Internal Server Error" HTML page — the frontend expects JSON.
    return JSONResponse(status_code=500, content={"detail": f"Ошибка сервера: {exc}"})

@app.on_event("startup")
def _warm_city_index():
    # Build the worldwide city index once at boot, so the first visitor is fast.
    try:
        geo._index()
    except Exception:
        pass  # falls back to online lookup on first use if this ever fails

@app.on_event("startup")
def _run_engine_selftest():
    # Run the calculation regression suite at boot so a broken engine surfaces
    # here rather than on someone's almanac. Never fatal: the gate blocks the
    # narrative per-request, and /api/verify reports why.
    r = verify.engine_selftest()
    if r["ok"]:
        print(f"[verify] engine self-test PASS — {r['passed']}/{r['total']} "
              f"({r['pass_rate']*100:.0f}%)")
    else:
        print(f"[verify] engine self-test FAIL — {r['pass_rate']*100:.0f}% "
              f"< {verify.THRESHOLD*100:.0f}% · error={r['error']} "
              f"· failed={r['failed_checks']}")

class BirthData(BaseModel):
    name: str = "Гость"
    date: str            # "YYYY-MM-DD"
    time: str = "12:00"  # "HH:MM"
    place: str | None = None
    lat: float | None = None
    lon: float | None = None
    tz: str | None = None

class LifeEvent(BaseModel):
    date: str                       # "YYYY" | "YYYY-MM" | "YYYY-MM-DD"
    category: str | None = None     # key from rectify.EVENTS, or None to auto-classify
    note: str = ""

class RectifyRequest(BirthData):
    events: list[LifeEvent] = []
    known_time: bool = True         # False => whole-day scan

class SynastryRequest(BaseModel):
    person_a: BirthData
    person_b: BirthData

def _build(data: BirthData):
    try:
        y, m, d = map(int, data.date.split("-"))
        hh, mm = map(int, data.time.split(":"))
        local_dt = datetime(y, m, d, hh, mm)
    except Exception:
        raise HTTPException(400, "Неверный формат даты/времени. Ожидается ГГГГ-ММ-ДД и ЧЧ:ММ.")
    try:
        loc = geo.resolve(data.place, data.lat, data.lon, data.tz)
    except ValueError as e:
        raise HTTPException(400, str(e))
    chart = jyotish.compute_chart(local_dt, loc["lat"], loc["lon"], loc["tz"])
    meta = f"{d:02d}.{m:02d}.{y} · {data.time} · {data.place or loc['label']}"
    return chart, loc, meta, local_dt

def _verified(chart, loc, local_dt):
    """Mandatory gate: calculation must be verified before any narrative is written.

    Raises 409 with the exact discrepancies rather than silently narrating a
    chart the two engines disagree about.
    """
    try:
        return verify.gate(chart, local_dt, loc["lat"], loc["lon"], loc["tz"])
    except verify.VerificationError as e:
        raise HTTPException(status_code=409, detail=e.report)

@app.post("/api/rectify")
def rectify(data: BirthData):
    """Step 1: compute lagna and return its description for confirmation."""
    chart, loc, meta, _local_dt = _build(data)
    desc = interpret.rectify_description(chart)
    a = chart["ascendant"]
    return {"ascendant": a, "location": loc, "meta": meta, "description": desc,
            "lagna_ru": a["sign_ru"]}

@app.post("/api/almanac")
def almanac(data: BirthData):
    """Step 2: full life-path almanac as standalone HTML.

    Order is mandatory: расчёт → верификация → нарратив. The narrative is only
    written after both verification barriers pass.
    """
    chart, loc, meta, local_dt = _build(data)
    verification = _verified(chart, loc, local_dt)     # ← blocks on failure
    narrative = interpret.generate_almanac(chart)
    html = render.render_almanac(data.name, meta, chart, narrative)
    return {"html": html, "meta": meta, "lagna_ru": chart["ascendant"]["sign_ru"],
            "has_ai": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "verification": verification}

@app.get("/api/geocode")
def geocode(place: str = ""):
    """Resolve a typed place name so the form can show which coordinates it will use.

    Kept separate from the chart endpoints: it is cheap, offline, and safe to call
    on every keystroke (debounced client-side).
    """
    place = (place or "").strip()
    if not place:
        raise HTTPException(400, "Укажите город.")
    try:
        return geo.resolve_place(place)
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.get("/api/events")
def event_catalog():
    """Category keys + human labels for the frontend dropdown."""
    return {"events": [{"key": k, "label": v["label"]} for k, v in rectify_engine.EVENTS.items()]}

@app.post("/api/rectify_events")
def rectify_events(data: RectifyRequest):
    """Step 1.2/1.3: reconstruct the lagna/birth-time from dated life events."""
    try:
        loc = geo.resolve(data.place, data.lat, data.lon, data.tz)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        y, m, d = map(int, data.date.split("-"))
        hh, mm = (map(int, data.time.split(":")) if data.time else (12, 0))
        base = datetime(y, m, d, hh, mm)
    except Exception:
        raise HTTPException(400, "Неверный формат даты рождения (ожидается ГГГГ-ММ-ДД).")
    events = [e.model_dump() for e in data.events]
    try:
        result = rectify_engine.rectify(base, loc["lat"], loc["lon"], loc["tz"],
                                        events, known_time=data.known_time)
    except ValueError as e:
        raise HTTPException(400, str(e))
    result["location"] = loc
    return result

@app.post("/api/synastry")
def synastry(req: SynastryRequest):
    """Step 4: two-chart compatibility as standalone HTML."""
    chart_a, loc_a, meta_a, dt_a = _build(req.person_a)
    chart_b, loc_b, meta_b, dt_b = _build(req.person_b)
    _verified(chart_a, loc_a, dt_a)                    # ← both charts must verify
    _verified(chart_b, loc_b, dt_b)
    syn = synastry_engine.compute_synastry(chart_a, chart_b,
                                           req.person_a.name or "Партнёр A",
                                           req.person_b.name or "Партнёр B")
    narrative = interpret.generate_synastry(syn)
    html = render.render_synastry(syn, narrative)
    return {"html": html, "ashtakoota": syn["ashtakoota"]["total"],
            "has_ai": bool(os.environ.get("ANTHROPIC_API_KEY"))}

@app.get("/api/health")
def health():
    engine = verify.engine_selftest()
    return {"ok": True, "ai": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "model": os.environ.get("JYOTISH_MODEL", "claude-sonnet-5"),
            "engine_verified": engine["ok"],
            "engine_pass_rate": engine["pass_rate"]}

@app.get("/api/verify")
def verify_status():
    """Full report of the engine regression suite — the `run-all` gate, as JSON."""
    engine = verify.engine_selftest()
    return {"threshold": verify.THRESHOLD, "engine": engine}

# ---- static frontend ----
@app.api_route("/", methods=["GET", "HEAD"])
def index():
    return FileResponse(FRONTEND / "index.html")

app.mount("/", StaticFiles(directory=str(FRONTEND)), name="static")
