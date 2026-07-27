# -*- coding: utf-8 -*-
"""Assemble the computed chart + SVGs + narrative into the full styled almanac HTML."""
import html as _h
from charts import natal_svg, vimshopaka_svg, sav_svg, bubble_svg, dignity_grid_html, _q
from jyotish import PL_RU

CSS = """
:root{--night:#14142b;--night2:#1c1c3a;--panel:#1a1a34;--gold:#c9a84c;--gold-soft:#e6cf8b;
--parch:#f4efe3;--plum:#7d5a86;--mute:#b9b4c9;--line:rgba(201,168,76,.22);
--green:#4f9d69;--blue:#4a7fb5;--yellow:#d9b23a;--red:#c25b5b;}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 80% -5%,#23234d 0,transparent 55%),
radial-gradient(900px 500px at 0 100%,#201b3a 0,transparent 50%),var(--night);
color:var(--parch);font-family:'Spectral',Georgia,serif;line-height:1.62;-webkit-font-smoothing:antialiased;}
.wrap{max-width:920px;margin:0 auto;padding:0 22px 90px;}
h1,h2,h3,.disp{font-family:'Cormorant Garamond',serif;font-weight:600;letter-spacing:.3px;}
.mono{font-family:'IBM Plex Mono',monospace;}
.hero{padding:54px 0 24px;text-align:center;}
.hero .eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:5px;text-transform:uppercase;color:var(--gold);opacity:.85;}
.hero h1{font-size:clamp(38px,8vw,70px);line-height:.98;margin:.16em 0 .08em;
background:linear-gradient(180deg,#fff 0,var(--gold-soft) 60%,var(--gold) 100%);-webkit-background-clip:text;background-clip:text;color:transparent;}
.hero .sub{color:var(--mute);font-size:17px;font-style:italic;}
.hero .meta{margin-top:14px;font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--plum);letter-spacing:1px;}
.chartwrap{display:flex;justify-content:center;margin:28px auto 8px;max-width:420px;}
.chart{width:100%;height:auto;overflow:visible;} .natal{filter:drop-shadow(0 10px 30px rgba(0,0,0,.4));}
section{margin-top:60px;}
.sec-head{display:flex;align-items:baseline;gap:16px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:24px;}
.sec-num{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--gold);border:1px solid var(--gold);border-radius:50%;width:34px;height:34px;min-width:34px;display:flex;align-items:center;justify-content:center;}
.sec-head h2{font-size:clamp(24px,4vw,34px);margin:0;}
p{margin:0 0 15px;} .prose{font-size:16.5px;white-space:pre-wrap;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:20px 22px;margin:16px 0;}
.callout{border-left:3px solid var(--gold);padding:4px 0 4px 18px;margin:18px 0;color:var(--gold-soft);font-style:italic;}
.thread{max-width:760px;margin:0 auto;padding:24px 28px;border:1px solid var(--line);border-radius:4px;
background:linear-gradient(180deg,rgba(244,239,227,.04),rgba(244,239,227,.01));font-size:18px;text-align:left;}
table{width:100%;border-collapse:collapse;font-size:14px;margin:14px 0;}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid rgba(201,168,76,.13);}
th{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--gold);font-weight:500;}
td.mono{font-family:'IBM Plex Mono',monospace;}
.grid{font-family:'IBM Plex Mono',monospace;font-size:12.5px;text-align:center;}
.grid th,.grid td{text-align:center;padding:6px 4px;} .grid td.pl{text-align:left;font-family:'Spectral',serif;white-space:nowrap;}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:5px;}
.legend{font-size:12px;color:var(--mute);font-family:'IBM Plex Mono',monospace;margin-top:8px;}
.pill{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:10.5px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);color:var(--gold-soft);margin-right:4px;}
.dasha-now td{background:rgba(201,168,76,.10);}
.tag{color:var(--green)} .tag.w{color:var(--red)} .tag.m{color:var(--yellow)} .tag.b{color:var(--blue)}
.foot{margin-top:60px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--plum);font-family:'IBM Plex Mono',monospace;line-height:1.9;}
"""

HEAD = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Джйотиш-Альманах · __NAME__</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Spectral:ital,wght@0,300;0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>%s</style></head><body><div class="wrap">""" % CSS

def _dasha_rows(chart):
    rows=""
    for md in chart["dasha"]:
        if md["age_start"]>96: continue
        now = md is chart["current_dasha"]
        cls=" class='dasha-now'" if now else ""
        mark="◀ " if now else ""
        rows+=(f"<tr{cls}><td>{mark}{md['lord_ru']}</td>"
               f"<td class='mono'>{md['start'].year}–{md['end'].year}</td>"
               f"<td class='mono'>{md['age_start']:.0f}–{md['age_end']:.0f}</td></tr>")
    return rows

def _yoga_cards(chart):
    if not chart["yogas"]:
        return "<div class='card'><p>Явных крупных натальных йог не обнаружено.</p></div>"
    out=""
    for y in chart["yogas"]:
        strong = "высокая" if y.get("strong") else "умеренная"
        out+=(f"<div class='card'><p style='margin:0 0 4px'><span class='pill'>{_h.escape(y['cat'])}</span>"
              f"<b style='font-size:18px'>{_h.escape(y['name'])}</b></p>"
              f"<p style='font-size:15px;margin:6px 0 0'><b>Механизм:</b> {_h.escape(y['mech'])} "
              f"<b>Сила:</b> {strong}.</p></div>")
    return out

def _section5_table(chart, player):
    sav=chart["sav_house"]
    theme={1:"«я», тело",2:"речь, деньги",3:"воля, усилие",4:"дом, покой",5:"дети, ум",
           6:"труд, здоровье",7:"партнёр, брак",8:"глубина, ресурсы",9:"судьба, вера",
           10:"карьера, дело",11:"доходы, круг",12:"уход, тайна"}
    rows=""
    for h in range(1,13):
        c,name=_q(sav[h],player[h])
        cls={"#4f9d69":"","#4a7fb5":"b","#d9b23a":"m","#c25b5b":"w"}[c]
        rows+=(f"<tr><td>{h} · {theme[h]}</td><td class='mono'>{sav[h]}</td>"
               f"<td class='mono'>{player[h]:.1f}</td><td><span class='tag {cls}'>{name}</span></td></tr>")
    return rows

def render_almanac(name, birth_meta, chart, narrative):
    esc=_h.escape
    bubble, player = bubble_svg(chart)
    a=chart["ascendant"]
    parts=[HEAD.replace("__NAME__", esc(name))]
    # hero
    parts.append(f"""<div class="hero">
      <div class="eyebrow">Джйотиш · Альманах жизненного пути</div>
      <h1>{esc(name)}</h1>
      <div class="sub">{a['sign_ru']}-лагна · {a['nakshatra']}</div>
      <div class="meta">{esc(birth_meta)} &nbsp;|&nbsp; Лахири · цельнознаковые дома</div>
      <div class="chartwrap">{natal_svg(chart)}</div></div>""")
    # 1 portrait
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">1</div><h2>Портрет одной нитью</h2></div>
      <div class="thread"><p class="prose" style="margin:0">{esc(narrative.get('portrait',''))}</p></div></section>""")
    # 2 shodashavarga
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">2</div><h2>Сила дробных карт</h2></div>
      <h3 style="color:var(--gold-soft);font-size:21px;margin:6px 0 4px">Сетка достоинств по 16 варгам</h3>
      <div class="tablewrap">{dignity_grid_html(chart)}</div>
      <p class="legend"><b>Э</b> экзальтация · <b>С</b> свой · <b>д</b> друг · <b>н</b> нейтрал · <b>в</b> враг · <b>П</b> падение</p>
      <div class="card">{vimshopaka_svg(chart)}<p class="legend" style="text-align:center">Вимшопака-балл (из 20)</p></div>
      <div class="card">{sav_svg(chart)}<p class="legend" style="text-align:center">Бинду по домам · ось X — номер дома</p></div>
      <p class="prose">{esc(narrative.get('shodashavarga',''))}</p></section>""")
    # 3 yogas
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">3</div><h2>Ключевые йоги</h2></div>
      <p class="prose">{esc(narrative.get('yogas',''))}</p>{_yoga_cards(chart)}</section>""")
    # 4 dasha
    ad=next((x for x in chart["antardashas"] if x["current"]),None)
    ad_line=(f"Сейчас: <b>{chart['current_dasha']['lord_ru']} · {ad['lord_ru']}</b> "
             f"(до {ad['end'].year}.{ad['end'].month:02d})." if ad else "")
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">4</div><h2>Вимшоттари — дуга жизни</h2></div>
      <div class="tablewrap"><table><thead><tr><th>Махадаша</th><th class="mono">Годы</th><th class="mono">Возраст</th></tr></thead>
      <tbody>{_dasha_rows(chart)}</tbody></table></div>
      <div class="callout">{ad_line}</div>
      <p class="prose">{esc(narrative.get('dasha',''))}</p></section>""")
    # 5 integral
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">5</div><h2>Интегральная карта судьбы</h2></div>
      <p>Каждый дом — это <b>поле</b> (бинду) и <b>игрок</b> (Вимшопака держателя). Ось X — сила поля, ось Y — сила игрока.</p>
      <div class="card" style="padding:14px">{bubble}</div>
      <div class="tablewrap"><table><thead><tr><th>Дом · сфера</th><th class="mono">Поле</th><th class="mono">Игрок</th><th>Тип</th></tr></thead>
      <tbody>{_section5_table(chart,player)}</tbody></table></div>
      <div class="card"><p class="prose" style="margin:0">{esc(narrative.get('integral',''))}</p></div></section>""")
    # 6 planets
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">6</div><h2>Как держать каждую планету в высшем состоянии</h2></div>
      <p class="prose">{esc(narrative.get('planets',''))}</p></section>""")
    note = narrative.get("_note","")
    parts.append(f"""<div class="foot">ДЖЙОТИШ-АЛЬМАНАХ · {esc(name)}<br>
      Лахири (сидерик) · цельнознаковые дома · Вимшопака по Шодашаварге · SAV · Вимшоттари · Swiss Ephemeris<br>
      Символический интерпретативный материал, не предсказание. {esc(note)}</div></div></body></html>""")
    return "".join(parts)


# ============================================================================
# Synastry (two-chart compatibility) renderer
# ============================================================================
def _guna_dial(total, mx=36):
    pct = total / mx
    W = 460; r = 90; cx = W/2; cy = 118; import math
    a0 = math.pi; a1 = math.pi*(1 - pct)
    def pt(a): return cx + r*math.cos(a), cy - r*math.sin(a)
    x0,y0 = pt(a0); x1,y1 = pt(a1); xe,ye = pt(0.0)
    col = "#4f9d69" if pct>=0.72 else "#c9a84c" if pct>=0.5 else "#c25b5b"
    large = 1 if (a0-a1) > math.pi else 0
    return f'''<svg viewBox="0 0 {W} 160" xmlns="http://www.w3.org/2000/svg" class="chart" style="max-width:360px">
      <path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 1 1 {xe:.1f} {ye:.1f}" fill="none" stroke="rgba(201,168,76,.15)" stroke-width="14" stroke-linecap="round"/>
      <path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{col}" stroke-width="14" stroke-linecap="round"/>
      <text x="{cx}" y="{cy-6}" text-anchor="middle" fill="{col}" font-size="40" font-family="Cormorant Garamond,serif" font-weight="600">{total:.0f}</text>
      <text x="{cx}" y="{cy+18}" text-anchor="middle" fill="#b9b4c9" font-size="13" font-family="IBM Plex Mono,monospace">из {mx}</text>
    </svg>'''

def _kuta_rows(ak):
    out=""
    for r in ak["rows"]:
        pct=r["score"]/r["max"]
        col="#4f9d69" if pct>=0.75 else "#c9a84c" if pct>=0.4 else "#c25b5b"
        out+=(f"<tr><td>{r['name']}</td>"
              f"<td class='mono' style='color:{col}'>{r['score']:g} / {r['max']}</td>"
              f"<td style='color:var(--mute);font-size:13px'>{r['meaning']}</td></tr>")
    return out

def _cmp_bars(rows, key_a, key_b, na, nb, unit=""):
    """two-column comparison bars for field/player."""
    mx=max(max(r[key_a],r[key_b]) for r in rows) or 1
    out="<div class='cmp'>"
    for r in rows:
        la=r.get("house") and f"дом {r['house']}" or r.get("planet","")
        wa=100*r[key_a]/mx; wb=100*r[key_b]/mx
        out+=(f"<div class='cmp-row'><span class='cmp-l'>{la}</span>"
              f"<span class='cmp-track'><i class='a' style='width:{wa:.0f}%'></i></span>"
              f"<span class='cmp-v mono'>{r[key_a]:g}</span>"
              f"<span class='cmp-track r'><i class='b' style='width:{wb:.0f}%'></i></span>"
              f"<span class='cmp-v mono'>{r[key_b]:g}</span></div>")
    out+="</div>"
    return out

def _overlay_html(items, host, guest):
    if not items: return f"<p style='color:var(--mute)'>{guest}: нет планет в ключевых домах {host}.</p>"
    li="".join(f"<li><b>{o['planet']}</b> {guest} → <b>{o['house']}-й дом</b> {host} <span style='color:var(--mute)'>({o['theme']})</span></li>" for o in items)
    return f"<ul class='overlay'>{li}</ul>"

SYN_CSS = """
.cmp{margin:10px 0;} .cmp-head{display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--gold);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;}
.cmp-row{display:grid;grid-template-columns:76px 1fr 34px 1fr 34px;align-items:center;gap:7px;margin-bottom:6px;font-size:13px;}
.cmp-l{color:var(--parch);} .cmp-v{color:var(--gold-soft);font-size:12px;text-align:center;}
.cmp-track{height:9px;border-radius:6px;background:rgba(201,168,76,.1);overflow:hidden;display:flex;}
.cmp-track i{height:100%;display:block;} .cmp-track i.a{background:linear-gradient(90deg,#4a7fb5,#8bb6c9);margin-left:auto;}
.cmp-track.r i.b{background:linear-gradient(90deg,#c9a84c,#e6cf8b);}
.overlay{list-style:none;padding:0;margin:6px 0;} .overlay li{padding:6px 0;border-bottom:1px solid rgba(201,168,76,.1);font-size:14.5px;}
.names{display:flex;gap:18px;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:12px;margin-top:6px;}
.names .a b{color:#8bb6c9;} .names .b b{color:var(--gold-soft);}
.tagset{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;}
.tagset span{font-family:'IBM Plex Mono',monospace;font-size:11px;padding:3px 10px;border-radius:20px;border:1px solid var(--line);}
"""

def render_synastry(syn, narrative):
    esc=_h.escape
    na=esc(syn["name_a"]); nb=esc(syn["name_b"])
    ak=syn["ashtakoota"]
    head=HEAD.replace("__NAME__", f"{na} × {nb}").replace("</style>", SYN_CSS+"</style>")
    p=[head]
    p.append(f"""<div class="hero">
      <div class="eyebrow">Джйотиш · Совместимость двух карт</div>
      <h1>{na} × {nb}</h1>
      <div class="sub">Аштакута · поле × игрок · интерсинастрия</div></div>""")
    # 1 Guna Milan
    verdict = ("сильная основа" if ak['total']>=25 else "рабочая совместимость" if ak['total']>=18 else "требует осознанности")
    p.append(f"""<section><div class="sec-head"><div class="sec-num">1</div><h2>Гуна Милан · Аштакута</h2></div>
      <div style="text-align:center">{_guna_dial(ak['total'])}
      <p style="color:var(--gold-soft);font-style:italic;margin-top:-6px">{verdict}</p></div>
      <div class="tablewrap"><table><thead><tr><th>Кута</th><th class="mono">Балл</th><th>Что показывает</th></tr></thead>
      <tbody>{_kuta_rows(ak)}</tbody></table></div>
      <p class="legend">Луна {na}: {syn['moon_a']['nak_name']} ({syn['moon_a']['sign_ru']}) · Луна {nb}: {syn['moon_b']['nak_name']} ({syn['moon_b']['sign_ru']})</p></section>""")
    # 2 field
    p.append(f"""<section><div class="sec-head"><div class="sec-num">2</div><h2>Сила ПОЛЯ — бинду по домам</h2></div>
      <div class="cmp-head"><span style="color:#8bb6c9">◧ {na}</span><span style="color:var(--gold-soft)">{nb} ◧</span></div>
      {_cmp_bars(syn['field'],'a','b',na,nb)}</section>""")
    # 3 players
    p.append(f"""<section><div class="sec-head"><div class="sec-num">3</div><h2>Сила ИГРОКОВ — Вимшопака</h2></div>
      <div class="cmp-head"><span style="color:#8bb6c9">◧ {na}</span><span style="color:var(--gold-soft)">{nb} ◧</span></div>
      {_cmp_bars(syn['players'],'a','b',na,nb)}</section>""")
    # 4 intersynastry
    p.append(f"""<section><div class="sec-head"><div class="sec-num">4</div><h2>Интерсинастрия — наложение карт</h2></div>
      <div class="card"><p style="margin:0 0 6px;color:var(--gold-soft)"><b>Планеты {nb} на домах {na}</b></p>{_overlay_html(syn['overlay_ab'], na, nb)}</div>
      <div class="card"><p style="margin:0 0 6px;color:#8bb6c9"><b>Планеты {na} на домах {nb}</b></p>{_overlay_html(syn['overlay_ba'], nb, na)}</div>
      <p class="prose">{esc(narrative.get('intersynastry',''))}</p>
      <p class="legend">Даракарака (тема партнёра) — {na}: {syn['dara_a']['pl_ru']} · {nb}: {syn['dara_b']['pl_ru']}</p></section>""")
    # 5 contrasts
    def houses_tags(hs):
        return "".join(f"<span>дом {h}</span>" for h in hs) or "<span style='color:var(--mute)'>—</span>"
    p.append(f"""<section><div class="sec-head"><div class="sec-num">5</div><h2>Контрасты и дополнения</h2></div>
      <div class="card"><p style="margin:0 0 4px;color:#4f9d69"><b>Дополнения</b> (один силён — другой опирается)</p><div class="tagset">{houses_tags(syn['complements'])}</div>
      <p style="margin:10px 0 4px;color:#4a7fb5"><b>Общая сила</b> (оба сильны — синергия/соперничество)</p><div class="tagset">{houses_tags(syn['shared'])}</div>
      <p style="margin:10px 0 4px;color:#c25b5b"><b>Зеркальная уязвимость</b> (оба слабы — беречь вместе)</p><div class="tagset">{houses_tags(syn['mirrors'])}</div></div>
      <p class="prose">{esc(narrative.get('contrasts',''))}</p></section>""")
    # 6 formula
    note=narrative.get("_note","")
    p.append(f"""<section><div class="sec-head"><div class="sec-num">6</div><h2>Формула пары</h2></div>
      <div class="thread"><p class="prose" style="margin:0">{esc(narrative.get('formula',''))}</p></div></section>
      <div class="foot">ДЖЙОТИШ · Совместимость · {na} × {nb}<br>
      Аштакута (Гуна Милан) 36 · SAV · Вимшопака · интерсинастрия · Swiss Ephemeris<br>
      Символический интерпретативный материал, не суждение о людях. {esc(note)}</div></div></body></html>""")
    return "".join(p)
