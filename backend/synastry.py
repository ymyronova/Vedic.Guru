# -*- coding: utf-8 -*-
"""
Synastry / compatibility of two charts.

Two layers:
  (1) Section-V style comparison used across the almanac —
      field (SAV per house), player (Vimshopaka per planet), and intersynastry
      (how each person's planets fall on the other's houses). Computed exactly.
  (2) Classical Ashtakoota / Guna Milan (36 points) from the two Moons —
      Varna, Vashya, Tara, Yoni, Graha-Maitri, Gana, Bhakoot, Nadi.

Where a classical sub-table is genuinely ambiguous across sources (Vashya, the
finer Yoni tiers) we use a documented simplification rather than fake precision.
All of this is symbolic interpretive material, never a judgement about people.
"""
from __future__ import annotations
import jyotish as j

# ----- nakshatra attribute tables (index 0..26) -----
GANA = (["Дэва","Манушья","Ракшаса"] * 9)  # placeholder, overwritten below
_GANA = {
 "Дэва":[0,4,6,7,12,14,16,21,26],
 "Манушья":[1,3,5,10,11,19,20,24,25],
 "Ракшаса":[2,8,9,13,15,17,18,22,23],
}
def _gana_of(n):
    for g,ns in _GANA.items():
        if n in ns: return g
    return "Манушья"

_NADI = {  # Aadi / Madhya / Antya
 "Ади":[0,5,6,11,12,17,18,23,24],
 "Мадхья":[1,4,7,10,13,16,19,22,25],
 "Антья":[2,3,8,9,14,15,20,21,26],
}
def _nadi_of(n):
    for k,ns in _NADI.items():
        if n in ns: return k
    return "Мадхья"

# Yoni animal per nakshatra
_YONI = ["Лошадь","Слон","Овца","Змея","Змея","Собака","Кошка","Овца","Кошка","Крыса",
         "Крыса","Корова","Буйвол","Тигр","Буйвол","Тигр","Олень","Олень","Собака","Обезьяна",
         "Мангуст","Обезьяна","Лев","Лошадь","Лев","Корова","Слон"]
_YONI_ENEMY = {frozenset(p) for p in [
    ("Корова","Тигр"),("Слон","Лев"),("Лошадь","Буйвол"),("Собака","Олень"),
    ("Обезьяна","Овца"),("Змея","Мангуст"),("Кошка","Крыса")]}

# Varna per Moon sign (0..11)
def _varna_rank(sign):
    if sign in (3,7,11): return 4   # water  -> Brahmin
    if sign in (0,4,8):  return 3   # fire   -> Kshatriya
    if sign in (1,5,9):  return 2   # earth  -> Vaishya
    return 1                        # air    -> Shudra

# Vashya class per Moon sign (simplified, degree splits for Sag/Cap)
def _vashya_class(sign, deg):
    if sign in (0,1): return "Ч"          # quadruped
    if sign in (2,5,6,10): return "Н"     # human
    if sign == 3 or sign == 11: return "Ж" # watery
    if sign == 4: return "Д"              # wild (Leo)
    if sign == 7: return "К"              # insect (Scorpio)
    if sign == 8: return "Н" if deg < 15 else "Ч"   # Sag
    if sign == 9: return "Ч" if deg < 15 else "Ж"   # Cap
    return "Н"

def _vashya_points(a, b):
    if a == b: return 2.0
    trio = {"Ч","Н","Ж"}
    if a in trio and b in trio: return 1.0
    return 0.5

def _tara(n1, n2):
    c = ((n2 - n1) % 27) + 1
    r = c % 9
    return 0.0 if r in (3, 5, 7) else 1.5

def _graha_maitri(lordA, lordB):
    def rel(x, y):
        if y in j.FRIENDS[x]: return "друг"
        if y in j.ENEMIES[x]: return "враг"
        return "нейтрал"
    ra, rb = rel(lordA, lordB), rel(lordB, lordA)
    pair = {ra, rb}
    if pair == {"друг"}: return 5.0
    if pair == {"друг","нейтрал"}: return 4.0
    if pair == {"нейтрал"}: return 3.0
    if pair == {"друг","враг"}: return 1.0
    if pair == {"нейтрал","враг"}: return 0.5
    return 0.0

def _gana_points(ga, gb):
    if ga == gb: return 6.0
    s = {ga, gb}
    if s == {"Дэва","Манушья"}: return 5.0
    if s == {"Дэва","Ракшаса"}: return 1.0
    return 0.0  # Manushya-Rakshasa

def _bhakoot(signA, signB):
    diff = (signB - signA) % 12
    return 0.0 if diff in (1, 11, 4, 8, 5, 7) else 7.0

def ashtakoota(a, b):
    """a,b: dicts with keys moon_nak(0..26), moon_sign(0..11), moon_deg."""
    varna = 1.0 if _varna_rank(a["moon_sign"]) >= _varna_rank(b["moon_sign"]) else 0.0
    vashya = _vashya_points(_vashya_class(a["moon_sign"],a["moon_deg"]),
                            _vashya_class(b["moon_sign"],b["moon_deg"]))
    tara = _tara(a["moon_nak"], b["moon_nak"]) + _tara(b["moon_nak"], a["moon_nak"])
    ya, yb = _YONI[a["moon_nak"]], _YONI[b["moon_nak"]]
    yoni = 4.0 if ya == yb else (0.0 if frozenset((ya, yb)) in _YONI_ENEMY else 2.0)
    gm = _graha_maitri(j.RULER[a["moon_sign"]], j.RULER[b["moon_sign"]])
    gana = _gana_points(_gana_of(a["moon_nak"]), _gana_of(b["moon_nak"]))
    bhak = _bhakoot(a["moon_sign"], b["moon_sign"])
    nadi = 0.0 if _nadi_of(a["moon_nak"]) == _nadi_of(b["moon_nak"]) else 8.0
    rows = [
        ("Варна", varna, 1, "духовная совместимость / рост"),
        ("Вашья", vashya, 2, "притяжение, влияние друг на друга"),
        ("Тара", tara, 3, "здоровье и благополучие связи"),
        ("Йони", yoni, 4, "телесная и инстинктивная совместимость"),
        ("Граха-майтри", gm, 5, "дружба умов, ментальная близость"),
        ("Гана", gana, 6, "темперамент и природа"),
        ("Бхакут", bhak, 7, "эмоциональная гармония, семья"),
        ("Нади", nadi, 8, "здоровье потомства, глубинная энергия"),
    ]
    total = round(sum(r[1] for r in rows), 1)
    return {"rows": [{"name":n,"score":s,"max":m,"meaning":d} for n,s,m,d in rows],
            "total": total, "max": 36}

def _moon_meta(chart):
    mo = chart["planets"]["Mo"]
    nak_i = int(mo["lon"] // (360/27))
    return {"moon_nak": nak_i, "moon_sign": mo["sign"], "moon_deg": mo["deg"],
            "nak_name": mo["nakshatra"], "sign_ru": mo["sign_ru"]}

def _overlay(host, guest):
    """Where guest's planets land in host's houses (house = guest_sign - host_lagna)."""
    lagna = host["lagna"]; out = []
    key_houses = {1:"личность/тело", 4:"дом/сердце", 5:"романтика/дети",
                  7:"партнёрство/близость", 10:"статус/дело", 11:"общие цели/круг"}
    for k, pl in guest["planets"].items():
        if k in ("Ra","Ke"): continue
        h = (pl["sign"] - lagna) % 12 + 1
        if h in key_houses:
            out.append({"planet": pl["name"], "house": h, "theme": key_houses[h]})
    order = {7:0,5:1,4:2,1:3,10:4,11:5}
    out.sort(key=lambda x: order.get(x["house"], 9))
    return out

def compute_synastry(a_chart, b_chart, name_a="Партнёр A", name_b="Партнёр B"):
    ma, mb = _moon_meta(a_chart), _moon_meta(b_chart)
    ak = ashtakoota(ma, mb)

    # field (SAV) & player (VB) side by side
    field = [{"house": h, "a": a_chart["sav_house"][h], "b": b_chart["sav_house"][h]}
             for h in range(1, 13)]
    players = [{"planet": j.PL_RU[p], "a": a_chart["vb"][p], "b": b_chart["vb"][p]}
               for p in ["Su","Mo","Ma","Me","Ju","Ve","Sa"]]

    # complements / mirror vulnerabilities / shared strengths (by field)
    complements, mirrors, shared = [], [], []
    for h in range(1, 13):
        sa, sb = a_chart["sav_house"][h], b_chart["sav_house"][h]
        if (sa >= 30 and sb < 25) or (sb >= 30 and sa < 25):
            complements.append(h)
        elif sa < 25 and sb < 25:
            mirrors.append(h)
        elif sa >= 30 and sb >= 30:
            shared.append(h)

    overlay_ab = _overlay(a_chart, b_chart)   # B's planets on A's houses
    overlay_ba = _overlay(b_chart, a_chart)   # A's planets on B's houses

    dk_a = a_chart["karakas"]["Даракарака"]; dk_b = b_chart["karakas"]["Даракарака"]

    return {
        "name_a": name_a, "name_b": name_b,
        "moon_a": ma, "moon_b": mb,
        "ashtakoota": ak,
        "field": field, "players": players,
        "complements": complements, "mirrors": mirrors, "shared": shared,
        "overlay_ab": overlay_ab, "overlay_ba": overlay_ba,
        "dara_a": dk_a, "dara_b": dk_b,
    }
