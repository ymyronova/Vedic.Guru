# -*- coding: utf-8 -*-
"""
Event-based birth-time rectification (dasha + transit method).

Idea: the birth time barely shifts the planets or the Vimshottari timeline over a
single day, but it rotates the LAGNA — and therefore which house each sign/planet
occupies and which house each dasha-lord rules. So a candidate time is scored by
how well the dasha running at each dated life event matches that event's natural
significators (houses + karakas), reinforced by slow-planet transits over those
houses. Candidates are ranked; the best lagna(s) are returned with transparent
per-event evidence for the user to confirm.

This is a symbolic interpretive aid, not a deterministic clock — it narrows and
proposes, the user confirms.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import jyotish as j

# ---- event taxonomy: category -> significator houses + karaka planets + label ----
EVENTS = {
    "marriage":      {"houses":[7,2,11], "karakas":["Ve"], "label":"Брак / свадьба"},
    "partnership":   {"houses":[7,11],   "karakas":["Ve"], "label":"Союз / серьёзные отношения"},
    "divorce":       {"houses":[6,8,12,7],"karakas":["Ve","Ma"], "label":"Развод / расставание"},
    "childbirth":    {"houses":[5,9],    "karakas":["Ju"], "label":"Рождение ребёнка"},
    "job_new":       {"houses":[10,6,11],"karakas":["Sa","Me","Su"], "label":"Новая работа / повышение"},
    "job_change":    {"houses":[10,6,7], "karakas":["Sa","Me"], "label":"Смена работы / карьеры"},
    "business":      {"houses":[7,10,11],"karakas":["Me","Ju"], "label":"Свой бизнес / дело"},
    "relocation":    {"houses":[4,3,12], "karakas":["Ma"], "label":"Переезд (в стране)"},
    "abroad":        {"houses":[12,9,7], "karakas":["Ra"], "label":"Переезд за границу"},
    "education":     {"houses":[4,5,9],  "karakas":["Me","Ju"], "label":"Учёба / диплom / степень"},
    "illness":       {"houses":[6,8,12], "karakas":["Sa","Ma"], "label":"Серьёзная болезнь"},
    "accident":      {"houses":[8,6],    "karakas":["Ma","Sa"], "label":"Травма / операция / авария"},
    "property":      {"houses":[4],      "karakas":["Ma","Ve"], "label":"Покупка жилья / имущества"},
    "wealth":        {"houses":[11,2,5,9],"karakas":["Ju","Ve"], "label":"Крупная прибыль / удача"},
    "loss":          {"houses":[12,8,6], "karakas":["Sa"], "label":"Крупная потеря / долг"},
    "parent_death":  {"houses":[4,9,8],  "karakas":["Su","Mo"], "label":"Уход родителя"},
    "spiritual":     {"houses":[9,12,8], "karakas":["Ke","Ju"], "label":"Духовный перелом"},
    "fame":          {"houses":[10,1,11],"karakas":["Su"], "label":"Признание / известность"},
}

# free-text keyword hints -> category (Russian + English)
KEYWORDS = {
    "marriage":["брак","свадьб","замуж","жени","married","wedding"],
    "divorce":["развод","расстав","divorce","separation"],
    "childbirth":["ребен","ребён","роди","дочь","сын","child","born","birth of"],
    "job_new":["работ","должност","повыш","new job","promotion","hired"],
    "job_change":["смена работ","уволил","career change","changed job","quit"],
    "business":["бизнес","дело","компан","business","startup","founded"],
    "relocation":["переезд","переех","move","moved","relocat"],
    "abroad":["заграниц","эмиграц","за границу","abroad","emigrat","visa"],
    "education":["универ","диплом","степен","school","degree","graduat","universit"],
    "illness":["болезн","диагноз","illness","disease","diagnos"],
    "accident":["операц","травм","авари","surgery","accident","injury"],
    "property":["квартир","дом куп","недвиж","house","apartment","property"],
    "wealth":["прибыл","выигр","наследств","wealth","windfall","inherit"],
    "loss":["потер","банкрот","долг","loss","bankrupt","debt"],
    "parent_death":["умер","смерть родит","death of","passed away","отец умер","мать умер"],
    "spiritual":["духовн","просветл","spiritual","awakening"],
    "fame":["слав","признан","награда","fame","award","recogni"],
}

def classify(text: str) -> str | None:
    t = (text or "").lower()
    for cat, kws in KEYWORDS.items():
        if any(k in t for k in kws):
            return cat
    return None

def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            d = datetime.strptime(s, fmt)
            if fmt == "%Y": d = d.replace(month=7, day=1)      # mid-year midpoint
            elif fmt == "%Y-%m": d = d.replace(day=15)
            return d
        except ValueError:
            continue
    return None

def _house_of(sign_idx: int, lagna: int) -> int:
    return (sign_idx - lagna) % 12 + 1

def _score_candidate(jd: float, lat: float, lon: float, birth_naive: datetime, events: list) -> dict:
    """Score one candidate birth time against all events. Higher = better fit."""
    pos = j.positions_at(jd)
    lagna = j._sidx(j.ascendant_at(jd, lat, lon))
    moon = pos["Mo"]
    lords = {h: j.RULER[(lagna + h - 1) % 12] for h in range(1, 13)}
    planet_house = {p: _house_of(j._sidx(pos[p]), lagna) for p in pos}

    total = 0.0; evidence = []
    for ev in events:
        H = set(ev["houses"]); K = set(ev["karakas"])
        md, ad = j.dasha_lords_at(moon, birth_naive, ev["date"])
        s = 0.0; why = []
        for lord, wt, tag in ((md, 1.0, "махадаша"), (ad, 0.6, "антардаша")):
            if lord is None: continue
            ruled = [h for h in range(1, 13) if lords[h] == lord]
            if any(h in H for h in ruled):
                hit = [h for h in ruled if h in H]
                s += 3.0 * wt; why.append(f"{tag} {j.PL_RU[lord]} управляет {hit[0]}-м домом")
            if planet_house.get(lord) in H:
                s += 1.5 * wt; why.append(f"{tag} {j.PL_RU[lord]} стоит в {planet_house[lord]}-м доме")
            if lord in K:
                s += 1.5 * wt; why.append(f"{tag} {j.PL_RU[lord]} — каракa темы")
        # slow-planet transit over an event house (from this candidate lagna)
        tr = j.transit_signs(ev["date"])
        for tp in ("Ju", "Sa"):
            th = _house_of(tr[tp], lagna)
            if th in H:
                s += 0.8; why.append(f"транзит {j.PL_RU[tp]} по {th}-му дому")
        total += s
        evidence.append({"label": ev["label"], "date": ev["date_str"],
                         "dasha": f"{j.PL_RU.get(md,'—')}/{j.PL_RU.get(ad,'—')}",
                         "score": round(s, 1), "why": why[:4]})
    return {"lagna": lagna, "lagna_ru": j.SIGNS_RU[lagna], "jd": jd,
            "score": round(total, 2), "evidence": evidence}

def rectify(birth_naive: datetime, lat: float, lon: float, tz: str,
            events_in: list, known_time: bool) -> dict:
    """
    events_in: [{'date': 'YYYY[-MM[-DD]]', 'category': key|None, 'note': str}]
    known_time: if True, search ±2h around given time in 3-min steps;
                if False, scan the whole day in 10-min steps then refine.
    """
    # normalise events
    events = []
    for e in events_in:
        d = parse_date(e.get("date", ""))
        cat = e.get("category") or classify(e.get("note", ""))
        if not d or not cat or cat not in EVENTS:
            continue
        meta = EVENTS[cat]
        events.append({"date": d, "date_str": e.get("date", ""),
                       "houses": meta["houses"], "karakas": meta["karakas"],
                       "label": meta["label"], "category": cat})
    if not events:
        raise ValueError("Не удалось распознать ни одного события. Укажите дату (хотя бы год) и тип события.")

    # candidate times
    def candidates(center: datetime, radius_min: int, step_min: int):
        n = radius_min // step_min
        for i in range(-n, n + 1):
            yield center + timedelta(minutes=i * step_min)

    base = birth_naive
    if known_time:
        cand_times = list(candidates(base, 120, 3))          # ±2h, 3-min steps
    else:
        day = base.replace(hour=0, minute=0)
        cand_times = [day + timedelta(minutes=10 * i) for i in range(0, 144)]  # whole day, 10-min

    scored = []
    for t in cand_times:
        jd = j.jd_from_local(t, tz)
        r = _score_candidate(jd, lat, lon, base, events)
        r["time"] = t.strftime("%H:%M")
        scored.append(r)

    # refine around the best if time was unknown (coarse->fine)
    if not known_time and scored:
        best = max(scored, key=lambda r: r["score"])
        center = datetime.strptime(best["time"], "%H:%M").replace(
            year=base.year, month=base.month, day=base.day)
        for t in candidates(center, 15, 2):
            jd = j.jd_from_local(t, tz)
            r = _score_candidate(jd, lat, lon, base, events)
            r["time"] = t.strftime("%H:%M"); scored.append(r)

    scored.sort(key=lambda r: -r["score"])
    best = scored[0]

    # group by lagna sign -> best candidate & its time-window per sign
    by_sign = {}
    for r in scored:
        by_sign.setdefault(r["lagna"], []).append(r)
    ranked_signs = []
    total_score = sum(max(0.01, v[0]["score"]) for v in by_sign.values()) or 1.0
    for lg, rows in by_sign.items():
        top = max(rows, key=lambda r: r["score"])
        times = sorted(r["time"] for r in rows)
        ranked_signs.append({
            "lagna": lg, "lagna_ru": j.SIGNS_RU[lg],
            "best_time": top["time"], "score": top["score"],
            "time_from": times[0], "time_to": times[-1],
            "share": round(100 * max(0.01, top["score"]) / total_score),
        })
    ranked_signs.sort(key=lambda x: -x["score"])
    # confidence: gap between #1 and #2 sign
    conf = "низкая"
    if len(ranked_signs) >= 2 and ranked_signs[0]["score"] > 0:
        gap = (ranked_signs[0]["score"] - ranked_signs[1]["score"]) / ranked_signs[0]["score"]
        conf = "высокая" if gap > 0.35 else "средняя" if gap > 0.15 else "низкая"
    elif len(ranked_signs) == 1:
        conf = "высокая"

    return {
        "best": {"time": best["time"], "lagna": best["lagna"], "lagna_ru": best["lagna_ru"],
                 "score": best["score"], "evidence": best["evidence"]},
        "ranked_signs": ranked_signs[:4],
        "confidence": conf,
        "n_events": len(events),
        "n_candidates": len(scored),
        "known_time": known_time,
    }
