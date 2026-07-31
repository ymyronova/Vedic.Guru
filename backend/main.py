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
from urllib.parse import quote
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import geo, jyotish, interpret, render, rectify as rectify_engine, synastry as synastry_engine
import pdfout, store, varshaphala, verify

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
    # Фокус разбора: general | career | money | love | other.
    # Меняет весь текст, поэтому входит в ключ кэша (см. _narrative_key).
    focus: str = "general"
    focus_note: str = ""     # своя тема, когда focus == "other"
    # Сколько годовых частей (Варшапхала) считать. 0 — только натал.
    # Число частей меняет и расчёт, и текст, поэтому входит в ключ кэша.
    years: int = 3
    year_from: int | None = None     # первый год; по умолчанию текущий

class LifeEvent(BaseModel):
    date: str                       # "YYYY" | "YYYY-MM" | "YYYY-MM-DD"
    category: str | None = None     # key from rectify.EVENTS, or None to auto-classify
    note: str = ""

class QAItem(BaseModel):
    q: str = ""
    a: str = ""

class AskRequest(BirthData):
    question: str = ""
    history: list[QAItem] = []

class RectifyRequest(BirthData):
    events: list[LifeEvent] = []
    known_time: bool = True         # False => whole-day scan

class AlmanacRequest(BirthData):
    # Пары «вопрос — ответ», которые человек выбрал вшить в отчёт. Не влияют на
    # ключ кэша: нарратив от них не зависит, меняется только сборка документа.
    qa: list[QAItem] = []

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


MAX_YEARS = 6


def _attach_years(chart: dict, data: BirthData, loc: dict, local_dt: datetime) -> None:
    """Годовые части считаются ДО шлюза, а не после.

    Их числа попадают и в документ, и в ответы на вопросы, поэтому проверять их
    надо там же, где натальные, — иначе годовой слой прошёл бы мимо барьера.
    Сбой расчёта одного года не должен ронять натальный отчёт: части просто не
    появятся, и это будет видно в ответе.
    """
    count = max(0, min(int(data.years or 0), MAX_YEARS))
    if not count:
        return
    try:
        chart["varsha"] = varshaphala.build_annual_parts(
            chart, local_dt, loc["lat"], loc["lon"], loc["tz"],
            count=count, place=data.place or loc["label"],
            start_year=data.year_from)
    except Exception as e:
        chart["varsha_error"] = f"{type(e).__name__}: {e}"

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
    # The prompt fingerprint is part of the key: editing the tone rules changes
    # it, so text written under the old prompt stops being found and regenerates.
    # The focus goes in too — it rewrites every section, so a career reading and
    # a love reading of the same chart are different texts, not one cached one.
    focus = (data.focus or "general").strip().lower()
    if focus not in interpret.FOCUS_KEYS:
        focus = "general"
    sig = focus if focus != "other" else "other:" + (data.focus_note or "").strip().lower()[:80]
    # Число годовых частей и стартовый год тоже в ключе: три года и один год —
    # разные тексты, и годы 2025+ отличаются от 2030+. Без этого возврат за
    # другим числом лет находил бы чужой кэш.
    years = max(0, min(int(getattr(data, "years", 0) or 0), MAX_YEARS))
    sig += f"|y{years}"
    if getattr(data, "year_from", None):
        sig += f"@{data.year_from}"
    return store.key_for(f"{kind}|{sig}", data.name, data.date, data.time,
                         loc["lat"], loc["lon"], loc["tz"],
                         interpret.prompt_fingerprint())

@app.post("/api/almanac")
def almanac(data: AlmanacRequest, refresh: bool = False):
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
    _attach_years(chart, data, loc, local_dt)
    verification = _verified(chart, loc, local_dt)     # ← blocks on failure

    key = _narrative_key("almanac", data, loc)
    if refresh:
        store.drop(key)
    narrative = store.get(key)
    cached = narrative is not None
    if not cached:
        narrative = interpret.generate_almanac(chart, data.focus, data.focus_note)
        # Годовой текст пишется отдельными запросами и складывается в тот же
        # объект: кэш один, значит повторный визит не платит ни за натальную
        # часть, ни за годовые.
        if chart.get("varsha"):
            narrative.update(interpret.generate_years(
                chart["varsha"], data.focus, data.focus_note))
        # Never cache a fallback: _note means Claude failed, and caching that
        # would freeze the template in place long after the cause was fixed.
        if not (narrative.get("_note") or narrative.get("_template")):
            store.put(key, narrative)

    flabel = interpret.focus_label(data.focus, data.focus_note)
    html = render.render_almanac(data.name, meta, chart, narrative,
                                 focus=None if data.focus in (None, "", "general") else flabel,
                                 qa=[p.model_dump() for p in data.qa])
    parts = chart.get("varsha") or []
    return {"html": html, "meta": meta, "lagna_ru": chart["ascendant"]["sign_ru"],
            "focus": flabel,
            # Reports whether Claude is usable, not merely whether a key is set.
            "has_ai": _ai_status()["status"] == "ok",
            "cached": cached,
            "years": [p["label"] for p in parts],
            # Сбой годового расчёта не роняет отчёт, но и не молчит: без этого
            # поля пропавшие годовые части выглядели бы как «так и задумано».
            "years_error": chart.get("varsha_error"),
            "verification": verification}

@app.post("/api/ask")
def ask(req: AskRequest):
    """Вопрос к готовому альманаху.

    Отвечает по тому же расчёту и в том же тоне, что и отчёт, и видит уже
    написанный нарратив — чтобы дополнять его, а не противоречить ему.
    Гейт верификации проходит и здесь: ответ ссылается на числа карты, значит
    карта должна быть проверена так же, как перед нарративом.
    """
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(400, "Пустой вопрос.")
    if len(q) > 1000:
        raise HTTPException(400, "Вопрос слишком длинный (до 1000 символов).")

    chart, loc, meta, local_dt = _build(req)
    _verified(chart, loc, local_dt)

    # Тот же нарратив, что и в отчёте, если он уже есть в кэше.
    narrative = store.get(_narrative_key("almanac", req, loc))

    key = store.key_for("ask|" + q.strip().lower()[:200],
                        req.name, req.date, req.time,
                        loc["lat"], loc["lon"], loc["tz"],
                        interpret.prompt_fingerprint())
    # Кэшируем только «холодный» вопрос без истории: с историей тот же вопрос
    # в другом контексте — это другой вопрос.
    reusable = not req.history
    out = store.get(key) if reusable else None
    if out is None:
        out = interpret.answer_question(
            chart, q, [h.model_dump() for h in req.history],
            req.focus, req.focus_note, narrative)
        if reusable and not out.get("_template"):
            store.put(key, out)
        cached = False
    else:
        cached = True
    return {"answer": out["answer"], "cached": cached,
            "ok": not out.get("_template")}

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
                        "", 0.0, 0.0, "", interpret.prompt_fingerprint())
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

class PdfRequest(BaseModel):
    html: str
    filename: str = "almanac"

@app.post("/api/pdf")
def to_pdf(req: PdfRequest):
    """Собрать PDF из готового HTML альманаха — один клик, без окна печати.

    HTML приходит от клиента, поэтому все внешние загрузки при рендере
    запрещены (см. pdfout). Документ самодостаточен, так что запрещать нечего.
    """
    ok, why = pdfout.available()
    if not ok:
        # 503, а не 500: движка просто нет — фронтенд по этому коду откатывается
        # на окно печати браузера, которое даёт тот же PDF в два клика.
        raise HTTPException(503, f"Серверная сборка PDF недоступна ({why}).")
    try:
        data = pdfout.html_to_pdf(req.html)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Не удалось собрать PDF: {type(e).__name__}: {e}")

    name = pdfout.safe_filename(req.filename)
    # RFC 5987: имя может быть кириллическим, поэтому ASCII-запасной вариант
    # плюс filename* в UTF-8.
    disposition = (f"attachment; filename=\"almanac.pdf\"; "
                   f"filename*=UTF-8''{quote(name + '.pdf')}")
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": disposition})

@app.get("/api/pdf")
def pdf_status():
    """Доступна ли серверная сборка PDF (и какой версией)."""
    ok, why = pdfout.available()
    return {"available": ok, "engine": "weasyprint" if ok else None, "detail": why}

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
# Без Cache-Control браузер вправе решать сам, насколько долго держать файл.
# index.html и app.js при этом истекают в разное время, и возможно худшее
# сочетание: свежая разметка со старым скриптом. Разметка тогда показывает
# кнопку, которой в старом скрипте не соответствует ни один обработчик, —
# нажатие молча не делает ничего, и это не отличить от поломки. no-cache не
# запрещает кэш, а требует каждый раз переспросить сервер: при совпадении ETag
# ответ 304 без тела, так что цена — один запрос, а разметка и скрипт всегда
# из одной сборки.
_REVALIDATE = "no-cache"

class _FreshStatic(StaticFiles):
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers.setdefault("Cache-Control", _REVALIDATE)
        return resp

@app.api_route("/", methods=["GET", "HEAD"])
def index():
    return FileResponse(FRONTEND / "index.html",
                        headers={"Cache-Control": _REVALIDATE})

app.mount("/", _FreshStatic(directory=str(FRONTEND)), name="static")
