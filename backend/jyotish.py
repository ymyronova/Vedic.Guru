# -*- coding: utf-8 -*-
"""
Jyotish computation engine.
Deterministic Vedic-astrology math on the Swiss Ephemeris (Lahiri, whole-sign houses).
Given local birth datetime + lat/lon + IANA timezone, returns the full chart:
planetary positions, 16 divisional charts, Vimshopaka-bala, Sarvashtakavarga,
Vimshottari dasha timeline, Jaimini karakas and the major natal yogas.
"""
from __future__ import annotations
import sys
import swisseph as swe
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Vimshopaka is delegated to evals/vimshopaka.py — the audited module with a
# weights checksum (Σ = 20), a self-test that fails the import on corrupted
# tables, and the Parashara 9-grade dignity scale. Adopted so the service and
# the eval suite compute the same number instead of two similar-looking ones.
_EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"
if str(_EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(_EVALS_DIR))
try:
    from vimshopaka import (compute_vimshopaka, analyse_sensitivity,
                            RU as _VP_RU)
    VIMSHOPAKA_AVAILABLE = True
except Exception:                      # module missing or tables corrupted
    VIMSHOPAKA_AVAILABLE = False

SIGNS_RU = ["Овен","Телец","Близнецы","Рак","Лев","Дева","Весы","Скорпион",
            "Стрелец","Козерог","Водолей","Рыбы"]
SIGNS_SHORT = ["Овн","Тлц","Блз","Рак","Лев","Дев","Вес","Скп","Стр","Кзр","Вдл","Рыб"]
PL_RU = {"Su":"Солнце","Mo":"Луна","Ma":"Марс","Me":"Меркурий","Ju":"Юпитер",
         "Ve":"Венера","Sa":"Сатурн","Ra":"Раху","Ke":"Кету"}
GLYPH = {"Su":"☉","Mo":"☽","Ma":"♂","Me":"☿","Ju":"♃","Ve":"♀","Sa":"♄","Ra":"☊","Ke":"☋"}
NAK = ["Ашвини","Бхарани","Криттика","Рохини","Мригашира","Ардра","Пунарвасу","Пушья",
       "Ашлеша","Магха","Пурва Пхалгуни","Уттара Пхалгуни","Хаста","Читра","Свати","Вишакха",
       "Анурадха","Джьештха","Мула","Пурва Ашадха","Уттара Ашадха","Шравана","Дхаништха",
       "Шатабхиша","Пурва Бхадрапада","Уттара Бхадрапада","Ревати"]
NAK_LORD = ["Ke","Ve","Su","Mo","Ma","Ra","Ju","Sa","Me"]  # cycles every 9
VIM_YEARS = {"Ke":7,"Ve":20,"Su":6,"Mo":10,"Ma":7,"Ra":18,"Ju":16,"Sa":19,"Me":17}
VIM_SEQ = ["Ke","Ve","Su","Mo","Ma","Ra","Ju","Sa","Me"]

RULER = {0:"Ma",1:"Ve",2:"Me",3:"Mo",4:"Su",5:"Me",6:"Ve",7:"Ma",8:"Ju",9:"Sa",10:"Sa",11:"Ju"}
EXALT = {"Su":0,"Mo":1,"Ma":9,"Me":5,"Ju":3,"Ve":11,"Sa":6}
DEBIL = {k:(v+6)%12 for k,v in EXALT.items()}
OWN   = {"Su":[4],"Mo":[3],"Ma":[0,7],"Me":[2,5],"Ju":[8,11],"Ve":[1,6],"Sa":[9,10]}
FRIENDS = {"Su":["Mo","Ma","Ju"],"Mo":["Su","Me"],"Ma":["Su","Mo","Ju"],"Me":["Su","Ve"],
           "Ju":["Su","Mo","Ma"],"Ve":["Me","Sa"],"Sa":["Me","Ve"]}
ENEMIES = {"Su":["Ve","Sa"],"Mo":[],"Ma":["Me"],"Me":["Mo"],"Ju":["Me","Ve"],
           "Ve":["Su","Mo"],"Sa":["Su","Mo","Ma"]}

VARGA_WEIGHTS = {"D1":3.5,"D2":1,"D3":1,"D4":0.5,"D7":0.5,"D9":3,"D10":0.5,"D12":0.5,
                 "D16":2,"D20":0.5,"D24":0.5,"D27":0.5,"D30":1,"D40":0.5,"D45":0.5,"D60":4}
DIGNITY_FRAC = {"Э":1.0,"МТ":1.0,"С":1.0,"д":0.75,"н":0.5,"в":0.25,"П":0.125}
PLAN_ORDER = ["Su","Mo","Ma","Me","Ju","Ve","Sa"]

# ---- Ashtakavarga benefic tables (houses from each contributor that give a bindu) ----
AV = {
 "Su":{"Su":[1,2,4,7,8,9,10,11],"Mo":[3,6,10,11],"Ma":[1,2,4,7,8,9,10,11],"Me":[3,5,6,9,10,11,12],"Ju":[5,6,9,11],"Ve":[6,7,12],"Sa":[1,2,4,7,8,9,10,11],"As":[3,4,6,10,11,12]},
 "Mo":{"Su":[3,6,7,8,10,11],"Mo":[1,3,6,7,10,11],"Ma":[2,3,5,6,9,10,11],"Me":[1,3,4,5,7,8,10,11],"Ju":[1,2,4,7,8,10,11],"Ve":[3,4,5,7,9,10,11],"Sa":[3,5,6,11],"As":[3,6,10,11]},
 "Ma":{"Su":[3,5,6,10,11],"Mo":[3,6,11],"Ma":[1,2,4,7,8,10,11],"Me":[3,5,6,11],"Ju":[6,10,11,12],"Ve":[6,8,11,12],"Sa":[1,4,7,8,9,10,11],"As":[1,3,6,10,11]},
 "Me":{"Su":[5,6,9,11,12],"Mo":[2,4,6,8,10,11],"Ma":[1,2,4,7,8,9,10,11],"Me":[1,3,5,6,9,10,11,12],"Ju":[6,8,11,12],"Ve":[1,2,3,4,5,8,9,11],"Sa":[1,2,4,7,8,9,10,11],"As":[1,2,4,6,8,10,11]},
 "Ju":{"Su":[1,2,3,4,7,8,9,10,11],"Mo":[2,5,7,9,11],"Ma":[1,2,4,7,8,10,11],"Me":[1,2,4,5,6,9,10,11],"Ju":[1,2,3,4,7,8,10,11],"Ve":[2,5,6,9,10,11],"Sa":[3,5,6,12],"As":[1,2,4,5,6,7,9,10,11]},
 "Ve":{"Su":[8,11,12],"Mo":[1,2,3,4,5,8,9,11,12],"Ma":[3,5,6,9,11,12],"Me":[3,5,6,9,11],"Ju":[5,8,9,10,11],"Ve":[1,2,3,4,5,8,9,10,11],"Sa":[3,4,5,8,9,10,11],"As":[1,2,3,4,5,8,9,11]},
 "Sa":{"Su":[1,2,4,7,8,10,11],"Mo":[3,6,11],"Ma":[3,5,6,10,11,12],"Me":[6,8,9,10,11,12],"Ju":[5,6,11,12],"Ve":[6,11,12],"Sa":[3,5,6,11],"As":[1,3,4,6,10,11]},
}

def _sidx(deg): return int((deg % 360)//30)
def _within(deg): return (deg % 360) - _sidx(deg)*30

# ---------------- divisional charts (return varga sign index 0-11) ----------------
def _D1(d): return _sidx(d)
def _D2(d):
    s=_sidx(d); w=_within(d); odd=(s%2==0)
    return (4 if w<15 else 3) if odd else (3 if w<15 else 4)
def _D3(d):
    s=_sidx(d); w=_within(d); return (s+int(w//10)*4)%12
def _D4(d):
    s=_sidx(d); w=_within(d); return (s+int(w//7.5)*3)%12
def _D7(d):
    s=_sidx(d); w=_within(d); start=s if s%2==0 else (s+6)%12
    return (start+int(w//(30/7)))%12
def _D9(d):
    s=_sidx(d); w=_within(d); part=int(w//(30/9))
    starts={0:0,4:0,8:0,1:9,5:9,9:9,2:6,6:6,10:6,3:3,7:3,11:3}
    return (starts[s]+part)%12
def _D10(d):
    s=_sidx(d); w=_within(d); start=s if s%2==0 else (s+8)%12
    return (start+int(w//3))%12
def _D12(d):
    s=_sidx(d); w=_within(d); return (s+int(w//2.5))%12
def _D16(d):
    s=_sidx(d); w=_within(d); start={0:0,1:4,2:8}[s%3]; return (start+int(w//(30/16)))%12
def _D20(d):
    s=_sidx(d); w=_within(d); start={0:0,1:8,2:4}[s%3]; return (start+int(w//1.5))%12
def _D24(d):
    s=_sidx(d); w=_within(d); start=4 if s%2==0 else 3; return (start+int(w//1.25))%12
def _D27(d):
    s=_sidx(d); w=_within(d); start={0:0,1:3,2:6,3:9}[s%4]; return (start+int(w//(30/27)))%12
def _D30(d):
    s=_sidx(d); w=_within(d); odd=(s%2==0)
    if odd:
        return 0 if w<5 else 10 if w<10 else 8 if w<18 else 2 if w<25 else 6
    return 1 if w<5 else 5 if w<12 else 11 if w<20 else 9 if w<25 else 7
def _D40(d):
    s=_sidx(d); w=_within(d); start=0 if s%2==0 else 6; return (start+int(w//0.75))%12
def _D45(d):
    s=_sidx(d); w=_within(d); start={0:0,1:4,2:8}[s%3]; return (start+int(w//(30/45)))%12
def _D60(d):
    s=_sidx(d); w=_within(d); return (s+int(w//0.5))%12

VARGAS = {"D1":_D1,"D2":_D2,"D3":_D3,"D4":_D4,"D7":_D7,"D9":_D9,"D10":_D10,"D12":_D12,
          "D16":_D16,"D20":_D20,"D24":_D24,"D27":_D27,"D30":_D30,"D40":_D40,"D45":_D45,"D60":_D60}

def _dignity(planet, sgn):
    if planet in ("Ra","Ke"): return "н"
    if planet in EXALT and sgn==EXALT[planet]: return "Э"
    if planet in DEBIL and sgn==DEBIL[planet]: return "П"
    if sgn in OWN[planet]: return "С"
    lord = RULER[sgn]
    if lord==planet: return "С"
    if lord in FRIENDS[planet]: return "д"
    if lord in ENEMIES[planet]: return "в"
    return "н"

def _fmt_dms(within):
    d=int(within); m=int(round((within-d)*60))
    if m==60: d+=1; m=0
    return f"{d}°{m:02d}′"

def compute_chart(local_dt: datetime, lat: float, lon: float, tz_name: str) -> dict:
    """local_dt: naive local wall-clock datetime; tz_name: IANA zone (e.g. 'Europe/Kiev')."""
    aware = local_dt.replace(tzinfo=ZoneInfo(tz_name))
    ut = aware.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute/60 + ut.second/3600, swe.GREG_CAL)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayan = swe.get_ayanamsa_ut(jd)

    pflags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    ids = {"Su":swe.SUN,"Mo":swe.MOON,"Ma":swe.MARS,"Me":swe.MERCURY,
           "Ju":swe.JUPITER,"Ve":swe.VENUS,"Sa":swe.SATURN}
    lon_p, speed = {}, {}
    for k,pid in ids.items():
        r = swe.calc_ut(jd, pid, pflags); lon_p[k]=r[0][0]; speed[k]=r[0][3]
    r = swe.calc_ut(jd, swe.MEAN_NODE, pflags)
    lon_p["Ra"]=r[0][0]; speed["Ra"]=r[0][3]
    lon_p["Ke"]=(lon_p["Ra"]+180)%360; speed["Ke"]=speed["Ra"]
    _, ascmc = swe.houses_ex(jd, lat, lon, b'A', swe.FLG_SIDEREAL)
    asc = ascmc[0]
    lagna = _sidx(asc)

    # planet dicts
    planets = {}
    for k in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]:
        s = _sidx(lon_p[k]); w=_within(lon_p[k])
        house = (s - lagna) % 12 + 1
        nak_i = int(lon_p[k] // (360/27))
        planets[k] = {
            "name": PL_RU[k], "glyph": GLYPH[k], "lon": round(lon_p[k],4),
            "sign": s, "sign_ru": SIGNS_RU[s], "deg": round(w,3), "dms": _fmt_dms(w),
            "house": house, "retro": speed[k] < 0 and k not in ("Ke",),
            "nakshatra": NAK[nak_i], "pada": int((lon_p[k] % (360/27))//(360/108))+1,
            "dignity": _dignity(k, s),
        }
    asc_nak = int(asc//(360/27))
    ascendant = {"lon": round(asc,4), "sign": lagna, "sign_ru": SIGNS_RU[lagna],
                 "deg": round(_within(asc),3), "dms": _fmt_dms(_within(asc)),
                 "nakshatra": NAK[asc_nak], "pada": int((asc%(360/27))//(360/108))+1}

    # ---- dignity grid + Vimshopaka ----
    # The grid is ours (it drives the varga table in the report). The score comes
    # from vimshopaka.py so it is checksum-verified and matches the eval suite.
    grid, vb = {}, {}
    for p in PLAN_ORDER:
        grid[p]={}
        for vname,vf in VARGAS.items():
            sgn=vf(lon_p[p]); dg=_dignity(p,sgn)
            grid[p][vname]={"sign": SIGNS_SHORT[sgn], "dignity": dg}

    vimshopaka = None
    if VIMSHOPAKA_AVAILABLE:
        vp_pos = {p: (_sidx(lon_p[p]), _within(lon_p[p])) for p in PLAN_ORDER}
        vimshopaka = compute_vimshopaka(vp_pos)
        vb = {p: vimshopaka["scores"][_VP_RU[p]] for p in PLAN_ORDER}
        # D60 spans 0°30' and carries the heaviest weight (4.0), so a planet a
        # few arcseconds from a boundary can swing ~2 points. Surface that rather
        # than presenting the score as exact.
        vimshopaka["sensitivity"] = analyse_sensitivity(vp_pos)
    else:
        for p in PLAN_ORDER:                     # legacy fallback scale
            tot = sum(VARGA_WEIGHTS[v]*DIGNITY_FRAC[grid[p][v]["dignity"]]
                      for v in VARGAS)
            vb[p] = round(tot, 2)

    # ---- Sarvashtakavarga ----
    pos = {k:_sidx(lon_p[k]) for k in PLAN_ORDER}; pos["As"]=lagna
    contribs=["Su","Mo","Ma","Me","Ju","Ve","Sa","As"]
    bav={}
    for p in AV:
        b=[0]*12
        for c in contribs:
            for h in AV[p][c]:
                b[(pos[c]+h-1)%12]+=1
        bav[p]=b
    sav_sign=[sum(bav[p][i] for p in bav) for i in range(12)]
    sav_house={h: sav_sign[(lagna+h-1)%12] for h in range(1,13)}

    # ---- Vimshottari dasha ----
    moon=lon_p["Mo"]; nak_span=360/27
    nak_i=int(moon//nak_span); lord=NAK_LORD[nak_i%9]
    frac=(moon-nak_i*nak_span)/nak_span
    balance=(1-frac)*VIM_YEARS[lord]
    def add_years(dt,y): return dt+timedelta(days=y*365.2425)
    seq=[]; cur=aware.replace(tzinfo=None); start_idx=VIM_SEQ.index(lord); first=True
    for cyc in range(2):
        for k in range(9):
            l=VIM_SEQ[(start_idx+k)%9]
            dur=balance if first else VIM_YEARS[l]
            end=add_years(cur,dur)
            seq.append({"lord":l,"lord_ru":PL_RU[l],"start":cur,"end":end,
                        "age_start":(cur-aware.replace(tzinfo=None)).days/365.2425,
                        "age_end":(end-aware.replace(tzinfo=None)).days/365.2425})
            cur=end; first=False
    now=datetime.utcnow(); current=None
    for md in seq:
        if md["start"]<=now<md["end"]: current=md
    antardashas=[]
    if current:
        l=current["lord"]; md_years=VIM_YEARS[l]; ai=VIM_SEQ.index(l); c2=current["start"]
        for k in range(9):
            al=VIM_SEQ[(ai+k)%9]; adur=md_years*VIM_YEARS[al]/120.0; aend=add_years(c2,adur)
            antardashas.append({"lord":al,"lord_ru":PL_RU[al],"start":c2,"end":aend,
                                "current": c2<=now<aend})
            c2=aend

    # ---- Jaimini chara karakas (7-scheme, Rahu excluded) ----
    kdeg={p:_within(lon_p[p]) for p in PLAN_ORDER}
    ordered=sorted(kdeg.items(), key=lambda x:-x[1])
    karaka_roles=["Атмакарака","Аматьякарака","Бхратрикарака","Матрикарака",
                  "Питрикарака","Гнатикарака","Даракарака"]
    karakas={}
    for i,(p,_) in enumerate(ordered):
        karakas[karaka_roles[i]]=p
    ak=karakas["Атмакарака"]
    karakamsa=_D9(lon_p[ak])   # AK sign in navamsa

    # ---- major natal yogas ----
    yogas=_detect_yogas(planets, lagna, vb, sav_house)

    return {
        "ayanamsa": round(ayan,4),
        "ut": ut.strftime("%Y-%m-%d %H:%M UTC"),
        "ascendant": ascendant,
        "planets": planets,
        "grid": grid,
        "vb": vb,
        "vimshopaka": vimshopaka,
        "sav_house": sav_house,
        "bav": bav,                      # per-planet bindu, for checksum verification
        "sav_avg": round(sum(sav_sign)/12,2),
        "dasha": seq,
        "current_dasha": current,
        "antardashas": antardashas,
        "karakas": {r:{"pl":p,"pl_ru":PL_RU[p]} for r,p in karakas.items()},
        "karakamsa": SIGNS_RU[karakamsa],
        "yogas": yogas,
        "lagna": lagna,
    }

def _detect_yogas(planets, lagna, vb, sav):
    """Detect the principal classical natal yogas actually present."""
    out=[]
    def sign_house(s): return (s-lagna)%12+1
    kendras={sign_house(planets[p]["sign"]) for p in planets}
    # Pancha Mahapurusha (Ma,Me,Ju,Ve,Sa own/exalt in a kendra)
    mahap={"Ma":"Ручака","Me":"Бхадра","Ju":"Ханса","Ve":"Малавья","Sa":"Шаша"}
    for p,nm in mahap.items():
        pl=planets[p]
        if pl["house"] in (1,4,7,10) and pl["dignity"] in ("Э","С","МТ"):
            out.append({"name":f"{nm}-йога","cat":"Панча-Махапуруша",
                        "mech":f"{pl['name']} в {'своём знаке' if pl['dignity'] in ('С','МТ') else 'экзальтации'} ({pl['sign_ru']}) в {pl['house']}-м доме (кендра).",
                        "strong": vb[p]>=12})
    # Amala: benefic in 10th from lagna
    tenth_sign=(lagna+9)%12
    benefics={"Ju","Ve","Me","Mo"}
    ten_occ=[p for p in planets if planets[p]["sign"]==tenth_sign and p in benefics]
    if ten_occ:
        out.append({"name":"Амала-йога","cat":"Репутация",
                    "mech":"Благодетель(и) "+", ".join(planets[p]["name"] for p in ten_occ)+" в 10-м доме от лагны — чистая, устойчивая репутация.",
                    "strong":True})
    # Gajakesari: Jupiter in kendra from Moon
    mh=planets["Mo"]["sign"]
    if (planets["Ju"]["sign"]-mh)%12 in (0,3,6,9):
        out.append({"name":"Гаджакесари-йога","cat":"Мудрость",
                    "mech":"Юпитер в кендре от Луны — ум, уважение, добрая слава.","strong":vb["Ju"]>=12})
    # Budha-Aditya: Sun & Mercury same sign
    if planets["Su"]["sign"]==planets["Me"]["sign"]:
        out.append({"name":"Будха-Адитья-йога","cat":"Интеллект",
                    "mech":"Солнце и Меркурий в одном знаке — острый ум, речь, способности.","strong":True})
    # Raja: 5th/9th lord conjunct 10th/1st/4th/7th lord (simplified: trikona lord with kendra lord same sign)
    lords={h: RULER[(lagna+h-1)%12] for h in range(1,13)}
    trik=[lords[5],lords[9],lords[1]]; kend=[lords[1],lords[4],lords[7],lords[10]]
    for t in set(trik):
        for k in set(kend):
            if t!=k and planets[t]["sign"]==planets[k]["sign"]:
                out.append({"name":"Раджа-йога","cat":"Статус",
                            "mech":f"{planets[t]['name']} (упр. тригоны) и {planets[k]['name']} (упр. кендры) соединены в {planets[t]['sign_ru']}.",
                            "strong": vb[t]>=11 and vb[k]>=11})
                break
    # Raja-yoga karaka: one planet ruling both a kendra and a trikona
    for p in PLAN_ORDER:
        houses_ruled=[h for h in range(1,13) if lords[h]==p]
        if any(h in (4,7,10) for h in houses_ruled) and any(h in (1,5,9) for h in houses_ruled) and len(houses_ruled)==2:
            out.append({"name":"Раджа-йога-карака","cat":"Йогакарака",
                        "mech":f"{planets[p]['name']} управляет и кендрой, и тригоной ({', '.join(str(h)+'-й' for h in houses_ruled)}).",
                        "strong":vb[p]>=11})
    # Dhana: lord of 2 and 11 same planet, well placed
    if lords[2]==lords[11]:
        p=lords[2]
        out.append({"name":"Дхана-йога","cat":"Богатство",
                    "mech":f"{planets[p]['name']} управляет 2-м и 11-м (обе оси богатства); сила {vb[p]}/20, дом {planets[p]['house']}.",
                    "strong":vb[p]>=13})
    # de-dup by name+mech
    seen=set(); uniq=[]
    for y in out:
        key=(y["name"],y["mech"])
        if key not in seen: seen.add(key); uniq.append(y)
    return uniq


# ============================================================================
# Helpers for rectification: positions / ascendant / dasha-at-date / transits
# ============================================================================
def jd_from_local(local_dt: datetime, tz_name: str) -> float:
    aware = local_dt.replace(tzinfo=ZoneInfo(tz_name))
    ut = aware.astimezone(ZoneInfo("UTC"))
    return swe.julday(ut.year, ut.month, ut.day,
                      ut.hour + ut.minute/60 + ut.second/3600, swe.GREG_CAL)

_PIDS = {"Su":swe.SUN,"Mo":swe.MOON,"Ma":swe.MARS,"Me":swe.MERCURY,
         "Ju":swe.JUPITER,"Ve":swe.VENUS,"Sa":swe.SATURN}

def positions_at(jd: float) -> dict:
    """Sidereal (Lahiri) longitudes of the 7 grahas + Rahu/Ketu at jd."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    out = {}
    for k, pid in _PIDS.items():
        out[k] = swe.calc_ut(jd, pid, flags)[0][0]
    ra = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0]
    out["Ra"] = ra; out["Ke"] = (ra + 180) % 360
    return out

def ascendant_at(jd: float, lat: float, lon: float) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _, ascmc = swe.houses_ex(jd, lat, lon, b'A', swe.FLG_SIDEREAL)
    return ascmc[0]

def vimshottari_sequence(moon_lon: float, birth_naive: datetime):
    """List of mahadashas [{lord,start,end}] covering ~120 years from birth."""
    nak_span = 360/27
    nak_i = int(moon_lon // nak_span)
    lord = NAK_LORD[nak_i % 9]
    frac = (moon_lon - nak_i*nak_span) / nak_span
    balance = (1 - frac) * VIM_YEARS[lord]
    def add_years(dt, y): return dt + timedelta(days=y*365.2425)
    seq = []; cur = birth_naive; start_idx = VIM_SEQ.index(lord); first = True
    for _cyc in range(2):
        for k in range(9):
            l = VIM_SEQ[(start_idx+k) % 9]
            dur = balance if first else VIM_YEARS[l]
            end = add_years(cur, dur)
            seq.append({"lord": l, "start": cur, "end": end}); cur = end; first = False
    return seq

def dasha_lords_at(moon_lon: float, birth_naive: datetime, target: datetime):
    """(mahadasha_lord, antardasha_lord) running on `target` date."""
    seq = vimshottari_sequence(moon_lon, birth_naive)
    md = next((m for m in seq if m["start"] <= target < m["end"]), None)
    if md is None:
        return (None, None)
    def add_years(dt, y): return dt + timedelta(days=y*365.2425)
    l = md["lord"]; ai = VIM_SEQ.index(l); c = md["start"]; md_years = VIM_YEARS[l]
    ad_lord = l
    for k in range(9):
        al = VIM_SEQ[(ai+k) % 9]; aend = add_years(c, md_years*VIM_YEARS[al]/120.0)
        if c <= target < aend:
            ad_lord = al; break
        c = aend
    return (l, ad_lord)

def transit_signs(target_utc: datetime) -> dict:
    """Sidereal sign index (0-11) of the slow movers on a date (for rectification)."""
    jd = swe.julday(target_utc.year, target_utc.month, target_utc.day, 12.0, swe.GREG_CAL)
    p = positions_at(jd)
    return {k: _sidx(p[k]) for k in ("Ju", "Sa", "Ra", "Ke")}
