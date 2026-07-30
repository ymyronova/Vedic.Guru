# -*- coding: utf-8 -*-
"""
Джйотиш-Альманах — API + static frontend.

Run:  uvicorn main:app --reload --port 8000   (from the backend/ folder)
Then open http://localhost:8000
"""
from __future__ import annotations
import os
import re
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import geo, jyotish, interpret, render, rectify as rectify_engine, synastry as synastry_engine
import store, verify

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
def _probe_ai_key():
    # Surface a broken key in the boot log instead of on someone's almanac.
    r = _ai_status(refresh=True)
    label = interpret.PROBE_LABELS.get(r["status"], r["status"])
    print(f"[ai] key probe: {r['status']} — {label}"
          + (f" · {r['detail']}" if r.get("detail") else ""))

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
def rectify(data: BirthData, refresh: bool = False):
    """Step 1: compute lagna and return its description for confirmation.

    The lagna description is a Claude call too, so it is cached on the same key.
    """
    chart, loc, meta, _local_dt = _build(data)
    key = _narrative_key("lagna", data, loc)
    if refresh:
        store.drop(key)
    desc = store.get(key)
    cached = desc is not None
    if not cached:
        desc = interpret.rectify_description(chart)
        if not desc.get("_template"):
            store.put(key, desc)
    a = chart["ascendant"]
    return {"ascendant": a, "location": loc, "meta": meta, "description": desc,
            "lagna_ru": a["sign_ru"], "cached": cached}

def _narrative_key(kind: str, data: BirthData, loc: dict) -> str:
    return store.key_for(kind, data.name, data.date, data.time,
                         loc["lat"], loc["lon"], loc["tz"])

@app.post("/api/almanac")
def almanac(data: BirthData, refresh: bool = False):
    """Step 2: full life-path almanac as standalone HTML.

    Order is mandatory: расчёт → верификация → нарратив. The narrative is only
    written after both verification barriers pass.

    The narrative is cached per birth data (see store.py). The chart, the
    verification gate and the HTML are rebuilt every time regardless: they cost
    milliseconds, the gate must run on every request rather than once, and
    caching rendered HTML would keep design changes from reaching anyone whose
    almanac already existed. ?refresh=1 forces regeneration.
    """
    chart, loc, meta, local_dt = _build(data)
    verification = _verified(chart, loc, local_dt)     # ← blocks on failure

    key = _narrative_key("almanac", data, loc)
    if refresh:
        store.drop(key)
    narrative = store.get(key)
    cached = narrative is not None
    if not cached:
        narrative = interpret.generate_almanac(chart)
        # Never cache a fallback: _note means Claude failed, and caching that
        # would freeze the template in place long after the cause was fixed.
        if not (narrative.get("_note") or narrative.get("_template")):
            store.put(key, narrative)

    html = render.render_almanac(data.name, meta, chart, narrative)
    return {"html": html, "meta": meta, "lagna_ru": chart["ascendant"]["sign_ru"],
            # Reports whether Claude is usable, not merely whether a key is set.
            "has_ai": _ai_status()["status"] == "ok",
            "cached": cached,
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
def synastry(req: SynastryRequest, refresh: bool = False):
    """Step 4: two-chart compatibility as standalone HTML."""
    chart_a, loc_a, meta_a, dt_a = _build(req.person_a)
    chart_b, loc_b, meta_b, dt_b = _build(req.person_b)
    _verified(chart_a, loc_a, dt_a)                    # ← both charts must verify
    _verified(chart_b, loc_b, dt_b)
    syn = synastry_engine.compute_synastry(chart_a, chart_b,
                                           req.person_a.name or "Партнёр A",
                                           req.person_b.name or "Партнёр B")

    # Keyed on both charts, so changing either partner regenerates.
    key = store.key_for("synastry",
                        _narrative_key("a", req.person_a, loc_a),
                        _narrative_key("b", req.person_b, loc_b),
                        "", 0.0, 0.0, "")
    if refresh:
        store.drop(key)
    narrative = store.get(key)
    cached = narrative is not None
    if not cached:
        narrative = interpret.generate_synastry(syn)
        if not (narrative.get("_note") or narrative.get("_template")):
            store.put(key, narrative)

    html = render.render_synastry(syn, narrative)
    return {"html": html, "ashtakoota": syn["ashtakoota"]["total"],
            # Reports whether Claude is usable, not merely whether a key is set.
            "has_ai": _ai_status()["status"] == "ok",
            "cached": cached}

_AI_STATUS: dict | None = None

def _ai_status(refresh: bool = False) -> dict:
    """Cached result of the key probe. Cached because it costs a real API call."""
    global _AI_STATUS
    if _AI_STATUS is None or refresh:
        _AI_STATUS = interpret.probe_key()
        _AI_STATUS["label"] = interpret.PROBE_LABELS.get(
            _AI_STATUS["status"], _AI_STATUS["status"])
    return _AI_STATUS

def _narrative_probe(sample: int = 0) -> dict:
    """Run the REAL narrative path once, on the reference chart.

    The 1-token key probe proves auth and credit only. It cannot catch the
    failures that actually silence the narrative — a response truncated by
    max_tokens, a rejected schema, or JSON that will not parse. This exercises
    the same code path an almanac uses and reports what came back.
    """
    try:
        ref = verify._reference_case()
        local = datetime.strptime(f"{ref['date']} {ref['time']}", "%Y-%m-%d %H:%M")
        chart = jyotish.compute_chart(local, float(ref["lat"]), float(ref["lon"]),
                                      ref.get("tz_name") or "UTC")
        nar = interpret.generate_almanac(chart)
        lengths = {k: len(str(nar.get(k, ""))) for k in interpret.ALMANAC_KEYS}
        templated = [k for k in interpret.ALMANAC_KEYS
                     if "(шаблон)" in str(nar.get(k, ""))]
        out = {"ok": nar.get("_note") is None and not templated,
               "note": nar.get("_note"),
               "templated_sections": templated,
               "section_lengths": lengths,
               "tone": _tone_report(nar),
               "max_tokens": interpret.NARRATIVE_MAX_TOKENS,
               "effort": interpret.EFFORT}
        if sample:
            out["sample"] = {k: str(nar.get(k, ""))[:sample]
                             for k in interpret.ALMANAC_KEYS}
        return out
    except Exception as e:
        return {"ok": False, "note": f"{type(e).__name__}: {e}"}


_SENTENCE = re.compile(r"[^.!?…]+[.!?…]")
_PAREN = re.compile(r"\([^()]{2,140}\)")

def _tone_report(nar: dict) -> dict:
    """How well the narrative follows the tone rule.

    The rule: a plain-language claim, then the chart parameter it rests on in
    parentheses. So a section that follows it has roughly one parenthetical per
    sentence or two; a section with none has reverted to unsourced assertion.
    """
    per_section, total_s, total_p = {}, 0, 0
    for k in interpret.ALMANAC_KEYS:
        text = str(nar.get(k, ""))
        s = len(_SENTENCE.findall(text)) or (1 if text.strip() else 0)
        p = len(_PAREN.findall(text))
        per_section[k] = {"sentences": s, "with_term": p,
                          "ratio": round(p / s, 2) if s else 0.0}
        total_s += s; total_p += p
    return {"per_section": per_section,
            "sentences": total_s, "terms": total_p,
            "terms_per_sentence": round(total_p / total_s, 2) if total_s else 0.0,
            "sections_without_terms": [k for k, v in per_section.items()
                                       if v["with_term"] == 0]}

@app.get("/api/ai")
def ai_status(refresh: bool = False, deep: bool = False, sample: int = 0):
    """Does the configured key actually work?

    ?refresh=1 re-runs the cheap key probe. ?deep=1 additionally generates a
    real narrative — slower and billed, but it is the only check that catches
    truncation and parse failures. ?sample=N includes the first N characters of
    each section, for eyeballing tone.
    """
    out = dict(_ai_status(refresh=refresh))
    if deep:
        out["narrative"] = _narrative_probe(sample=max(0, min(sample, 2000)))
    return out

@app.get("/api/health")
def health():
    engine = verify.engine_selftest()
    ai = _ai_status()
    return {"ok": True,
            # kept as a bool for backwards compatibility: true means "usable",
            # not merely "the env var is set" — that distinction was the bug.
            "ai": ai["status"] == "ok",
            "ai_status": ai["status"],
            "ai_detail": ai.get("label"),
            "model": os.environ.get("JYOTISH_MODEL", "claude-sonnet-5"),
            "engine_verified": engine["ok"],
            "engine_pass_rate": engine["pass_rate"]}

@app.get("/api/cache")
def cache_stats():
    """Narrative cache counters — hits, misses, entries, and where they live."""
    return store.stats()

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
