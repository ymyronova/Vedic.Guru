# -*- coding: utf-8 -*-
"""
Слой верификации: расчёт → проверка → нарратив. Никогда не наоборот.

Два независимых барьера, оба обязаны пройти до генерации нарратива:

  1. Регрессия движка (engine_selftest)
     Прогоняет эталонный кейс (Анна, 21.12.1976) из evals.json через
     evals/verify_chart.py и сверяет с ground_truth. Это ровно то, что делает
     `python evals/verify_chart.py run-all`. Считается один раз при старте.

  2. Кросс-проверка конкретной карты (cross_check)
     Пересчитывает карту пользователя вторым, независимым движком
     (evals/verify_chart.py) и сравнивает с тем, что выдал backend/jyotish.py.
     Барьер 1 сам по себе НЕ проверяет jyotish.py — он проверяет только
     эталонный верификатор. Без этого шага гейт давал бы ложную уверенность.

Порог — 0.90 (grading_rubric.layer_1_calculation.pass_threshold в evals.json).
Дополнительно: расхождение по ЗНАКУ любой планеты или по лагне блокирует
генерацию независимо от процента — см. README, «ошибка в знаке одной планеты
= провал всего тест-кейса».
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

# evals/ lives next to backend/ in the repo and is COPYed into the image.
EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"
EVALS_JSON = EVALS_DIR / "evals.json"

THRESHOLD = 0.90

# jyotish.py keys -> verify_chart.py keys
_KEYMAP = {"Su": "sun", "Mo": "moon", "Ma": "mars", "Me": "mercury",
           "Ju": "jupiter", "Ve": "venus", "Sa": "saturn",
           "Ra": "rahu", "Ke": "ketu"}

# Ketu's retrograde flag is a convention difference, not a calculation error:
# jyotish.py reports False, verify_chart.py hardcodes True. Comparing it would
# manufacture a permanent false mismatch.
_SKIP_RETRO = {"Ke"}

# --- Ashtakavarga invariants (evals.json #11) --------------------------------
# These totals are fixed for every chart regardless of birth data: they follow
# from the benefic-point tables alone. A drift means the tables were edited.
SAV_TOTAL = 337
BAV_TOTALS = {"Su": 48, "Mo": 49, "Ma": 39, "Me": 54,
              "Ju": 56, "Ve": 52, "Sa": 39}
HOUSE_BINDU_RANGE = (18, 42)

# --- Vimshopaka invariants (evals.json #13) ----------------------------------
VARGA_COUNT = 16
WEIGHTS_TOTAL = 20.0
VB_RANGE = (3.0, 20.0)
VB_TOLERANCE = 0.05


def _norm_name(s: str) -> str:
    """Collapse transliteration differences between the two engines.

    The nakshatra lists are the same 27 in the same order, spelled differently:
    jyotish.py writes «Пурва Ашадха», verify_chart.py «Пурвашадха». Lowercasing,
    dropping non-letters and collapsing doubled letters makes all 27 agree, and
    genuinely different nakshatras still compare unequal.
    """
    s = re.sub(r"[^\w]", "", (s or "").lower())
    out: list[str] = []
    for ch in s:
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


class VerificationError(Exception):
    """Raised when a chart must not proceed to narrative generation."""

    def __init__(self, report: dict):
        self.report = report
        super().__init__(report.get("message", "verification failed"))


@lru_cache(maxsize=1)
def _verifier():
    """Import evals/verify_chart.py as a module (it is a CLI script by design)."""
    if str(EVALS_DIR) not in sys.path:
        sys.path.insert(0, str(EVALS_DIR))
    import verify_chart
    return verify_chart


@lru_cache(maxsize=1)
def _evals() -> dict:
    with open(EVALS_JSON, encoding="utf-8") as f:
        return json.load(f)


def _reference_case() -> dict:
    """Birth data of the canonical regression case, from evals.json."""
    ref = _evals().get("meta", {}).get("reference_birth_data")
    if not ref:  # older evals.json without the machine-readable block
        return {"date": "1976-12-21", "time": "10:32",
                "lat": 47.233, "lon": 39.717, "tz_offset": 3.0}
    return ref


def _ground_truth() -> dict:
    """Assemble the layer-1 ground truth (planets + nakshatra + current MD)."""
    evals = _evals().get("evals", [])
    gt = {"planets_sidereal": {}, "moon_nakshatra": {}, "current_mahadasha": ""}
    for e in evals:
        g = e.get("ground_truth") or {}
        if g.get("planets_sidereal") and not gt["planets_sidereal"]:
            gt["planets_sidereal"] = g["planets_sidereal"]
            moon = g["planets_sidereal"].get("moon", {})
            if moon.get("nakshatra"):
                gt["moon_nakshatra"] = {"name": moon["nakshatra"]}
        if g.get("current_mahadasha") and not gt["current_mahadasha"]:
            gt["current_mahadasha"] = g["current_mahadasha"]
    return gt


@lru_cache(maxsize=1)
def engine_selftest() -> dict:
    """Barrier 1 — the `run-all` regression suite, evaluated in-process.

    Cached: the reference case is static, so this runs once per process.
    """
    try:
        vc = _verifier()
        ref = _reference_case()
        chart = vc.calculate_chart(ref["date"], ref["time"],
                                   float(ref["lat"]), float(ref["lon"]),
                                   float(ref["tz_offset"]))
        result = vc.verify_against_ground_truth(chart, _ground_truth())
        rate = result["summary"]["pass_rate"]
        return {
            "ok": rate >= THRESHOLD,
            "pass_rate": rate,
            "passed": result["summary"]["passed"],
            "total": result["summary"]["total"],
            "failed_checks": [c["check"] for c in result["checks"] if not c["passed"]],
            "error": None,
        }
    except Exception as e:                      # never take the service down
        return {"ok": False, "pass_rate": 0.0, "passed": 0, "total": 0,
                "failed_checks": [], "error": f"{type(e).__name__}: {e}"}


def _tz_offset_hours(local_dt: datetime, tz_name: str) -> float:
    """Historical UTC offset for that wall-clock moment (Kyiv 1988 = +4, not +2)."""
    return local_dt.replace(tzinfo=ZoneInfo(tz_name)).utcoffset().total_seconds() / 3600.0


def _add_ashtakavarga_checks(chart: dict, add) -> None:
    """evals.json #11 — the eight Ashtakavarga checksums.

    Fixed for any chart, so a failure means the benefic-point tables drifted,
    not that this particular birth data is unusual. Critical: bindu drive the
    'which area of life is strong' claims in the report.
    """
    sav = chart.get("sav_house")
    if not sav:
        add("Аштакаварга рассчитана", False, "sav_house отсутствует в карте",
            critical=True)
        return

    total = sum(sav.values())
    add(f"Контрольная сумма САВ = {SAV_TOTAL}", total == SAV_TOTAL,
        f"получено: {total}", critical=True)

    bav = chart.get("bav") or {}
    bad = []
    for code, expected in BAV_TOTALS.items():
        got = sum(bav.get(code, []))
        if got != expected:
            bad.append(f"{code}: {got}≠{expected}")
    add("Контрольные суммы БАВ 7 планет", not bad,
        ", ".join(bad) if bad else "все 7 совпали", critical=True)

    lo, hi = HOUSE_BINDU_RANGE
    out = [f"{h}-й дом: {v}" for h, v in sorted(sav.items()) if not lo <= v <= hi]
    add(f"Бинду каждого дома в диапазоне {lo}–{hi}", not out,
        ", ".join(out) if out else "все 12 домов в диапазоне")


def _add_vimshopaka_checks(chart: dict, ref: dict, add) -> None:
    """evals.json #13/#14 — Vimshopaka invariants and an independent score check.

    The score check is deliberately NOT chart['vb'] against the same module fed
    with the same positions — that would be circular, since jyotish.py already
    delegates to vimshopaka.py. Instead the REFERENCE engine's positions are fed
    through the module and compared against our score, so a positional
    divergence that moves a varga boundary is caught.
    """
    vp = chart.get("vimshopaka")
    if not vp:
        add("Вимшопака рассчитана", False,
            "модуль vimshopaka.py недоступен — балл не проверен")
        return

    v = vp.get("validation", {})
    add(f"Сумма весов 16 варг = {WEIGHTS_TOTAL}", v.get("weights_ok") is True,
        f"получено: {v.get('weights_total')}", critical=True)
    add(f"Число варг = {VARGA_COUNT}", v.get("varga_count") == VARGA_COUNT,
        f"получено: {v.get('varga_count')}")

    lo, hi = VB_RANGE
    bad = [f"{n}: {s}" for n, s in vp.get("scores", {}).items()
           if not lo <= s <= hi]
    add(f"Все ВБ в диапазоне {lo}–{hi}", not bad,
        ", ".join(bad) if bad else "все 7 в диапазоне")

    # Independent recomputation from the reference engine's positions.
    try:
        import vimshopaka as _vp_mod
    except Exception as e:
        add("Вимшопака: перекрёстная сверка", False, f"модуль недоступен: {e}")
        return

    ref_pos = {}
    for code, en in _KEYMAP.items():
        if code not in _vp_mod.PLANETS:
            continue
        r = ref["planets"].get(en)
        if not r:
            add(f"Вимшопака: позиция {en} из эталона", False, "отсутствует")
            return
        ref_pos[code] = (r["sign_index"], r["degree_in_sign"])

    try:
        ref_vp = _vp_mod.compute_vimshopaka(ref_pos)
    except Exception as e:
        add("Вимшопака по эталонным позициям", False, f"{type(e).__name__}: {e}")
        return

    mismatched = []
    for code in _vp_mod.PLANETS:
        ours = chart["vb"].get(code)
        theirs = ref_vp["scores"][_vp_mod.RU[code]]
        if ours is None or abs(ours - theirs) > VB_TOLERANCE:
            mismatched.append(f"{_vp_mod.RU[code]}: {ours} vs {theirs}")
    add(f"ВБ совпадает с расчётом по эталонным позициям (±{VB_TOLERANCE})",
        not mismatched, ", ".join(mismatched) if mismatched else "все 7 совпали")


def cross_check(chart: dict, local_dt: datetime, lat: float, lon: float,
                tz_name: str) -> dict:
    """Barrier 2 — recompute this chart with the second engine and compare."""
    vc = _verifier()
    offset = _tz_offset_hours(local_dt, tz_name)
    ref = vc.calculate_chart(local_dt.strftime("%Y-%m-%d"),
                             local_dt.strftime("%H:%M"), lat, lon, offset)

    checks: list[dict] = []

    def add(name, passed, evidence, critical=False):
        checks.append({"check": name, "passed": bool(passed),
                       "evidence": evidence, "critical": critical})

    # Lagna — a sign mismatch here shifts every house in the chart.
    svc_asc = chart["ascendant"]["sign_ru"]
    ref_asc = ref["ascendant"]["sign"]
    add("Лагна", svc_asc == ref_asc,
        f"сервис: {svc_asc} {chart['ascendant']['deg']:.2f}° · "
        f"эталон: {ref_asc} {ref['ascendant']['degree_in_sign']:.2f}°",
        critical=True)

    for k, en in _KEYMAP.items():
        p = chart["planets"].get(k)
        r = ref["planets"].get(en)
        if not p or not r:
            add(f"{en}: присутствует в обоих расчётах", False,
                f"сервис={bool(p)} эталон={bool(r)}", critical=True)
            continue
        add(f"{p['name']}: знак", p["sign_ru"] == r["sign"],
            f"сервис: {p['sign_ru']} {p['deg']:.2f}° · эталон: {r['sign']} {r['degree_in_sign']:.2f}°",
            critical=True)
        add(f"{p['name']}: дом", p["house"] == r["house"],
            f"сервис: {p['house']}-й · эталон: {r['house']}-й")
        if k not in _SKIP_RETRO:
            add(f"{p['name']}: ретроградность", p["retro"] == r["retrograde"],
                f"сервис: {p['retro']} · эталон: {r['retrograde']}")

    # Moon nakshatra drives the whole Vimshottari sequence.
    svc_nak = chart["planets"]["Mo"]["nakshatra"]
    ref_nak = ref["moon_nakshatra"]["name"]
    add("Накшатра Луны", _norm_name(svc_nak) == _norm_name(ref_nak),
        f"сервис: {svc_nak} · эталон: {ref_nak}", critical=True)

    svc_md = (chart.get("current_dasha") or {}).get("lord_ru") or "—"
    ref_md = ref.get("current_mahadasha", "—")
    add("Текущая махадаша", svc_md == ref_md, f"сервис: {svc_md} · эталон: {ref_md}")

    _add_ashtakavarga_checks(chart, add)
    _add_vimshopaka_checks(chart, ref, add)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    rate = round(passed / total, 3) if total else 0.0
    critical_failures = [c for c in checks if not c["passed"] and c["critical"]]

    return {
        "ok": rate >= THRESHOLD and not critical_failures,
        "pass_rate": rate,
        "passed": passed,
        "total": total,
        "critical_failures": [c["check"] for c in critical_failures],
        "failures": [{"check": c["check"], "evidence": c["evidence"]}
                     for c in checks if not c["passed"]],
    }


def gate(chart: dict, local_dt: datetime, lat: float, lon: float,
         tz_name: str) -> dict:
    """Run both barriers. Raise VerificationError if narrative must not proceed."""
    engine = engine_selftest()
    if not engine["ok"]:
        raise VerificationError({
            "stage": "engine_selftest",
            "message": ("Регрессия расчётного движка не пройдена "
                        f"({engine['pass_rate']*100:.0f}% < {THRESHOLD*100:.0f}%). "
                        "Генерация нарратива заблокирована."),
            "threshold": THRESHOLD,
            "engine": engine,
        })

    chk = cross_check(chart, local_dt, lat, lon, tz_name)
    if not chk["ok"]:
        reason = ("расхождение по знаку/лагне: " + ", ".join(chk["critical_failures"])
                  if chk["critical_failures"]
                  else f"{chk['pass_rate']*100:.0f}% < {THRESHOLD*100:.0f}%")
        raise VerificationError({
            "stage": "cross_check",
            "message": ("Два независимых движка разошлись в расчёте карты "
                        f"({reason}). Генерация нарратива заблокирована."),
            "threshold": THRESHOLD,
            "engine": engine,
            "cross_check": chk,
        })

    return {"engine": engine, "cross_check": chk, "threshold": THRESHOLD}
