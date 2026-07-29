# -*- coding: utf-8 -*-
"""Assemble the computed chart + SVGs + narrative into the full styled almanac HTML."""
import html as _h
import theme
from charts import natal_svg, vimshopaka_svg, sav_svg, bubble_svg, dignity_grid_html, _q
from jyotish import PL_RU

CSS = """
:root{--paper:%(PAPER)s;--panel:%(PANEL)s;--panel2:%(PANEL2)s;
--accent:%(ACCENT)s;--accent2:%(ACCENT2)s;--wash:%(ACCENT_WASH)s;--soft:%(ACCENT_SOFT)s;
--ink:%(INK)s;--muted:%(MUTED)s;--faint:%(FAINT)s;
--line:%(LINE)s;--line-soft:%(LINE_SOFT)s;
--green:%(GREEN)s;--blue:%(BLUE)s;--yellow:%(YELLOW)s;--red:%(RED)s;--saturn:%(SATURN)s;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font-family:%(SERIF)s;line-height:1.68;-webkit-font-smoothing:antialiased;}
.wrap{max-width:940px;margin:0 auto;padding:0 24px 60px;}
h1,h2,h3,.disp{font-family:%(DISPLAY)s;font-weight:600;letter-spacing:.2px;color:var(--ink);}
.mono{font-family:%(MONO)s;}
.jy{color:var(--faint);font-size:.86em;font-style:italic;}

.hero{padding:40px 0 26px;text-align:center;}
.hero .eyebrow{font-family:%(MONO)s;font-size:10px;letter-spacing:5px;text-transform:uppercase;color:var(--accent);margin-bottom:10px;}
.hero h1{font-size:clamp(38px,7.5vw,64px);line-height:1;margin:.1em 0;color:var(--accent);}
.hero .sub{color:var(--muted);font-size:17px;font-style:italic;margin-bottom:6px;}
.hero .meta{margin-top:10px;font-family:%(MONO)s;font-size:11px;color:var(--faint);letter-spacing:1px;}
.focus-badge{display:inline-block;margin-top:16px;padding:5px 18px;border:1px solid var(--line);border-radius:20px;
font-family:%(MONO)s;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:var(--accent2);background:var(--wash);}
.chartwrap{display:flex;justify-content:center;margin:26px auto 10px;max-width:400px;}
.chart{width:100%%;height:auto;overflow:visible;}
.natal{filter:drop-shadow(0 4px 14px rgba(0,0,0,.10));}

section{margin-top:0;}
.sec-head{display:flex;align-items:baseline;gap:16px;border-bottom:2px solid var(--line);padding-bottom:12px;margin-bottom:22px;}
.sec-num{font-family:%(MONO)s;font-size:12px;color:#fff;background:var(--accent);border:none;border-radius:50%%;
width:34px;height:34px;min-width:34px;display:flex;align-items:center;justify-content:center;}
.sec-head h2{font-size:clamp(24px,4.2vw,33px);margin:0;}
.sec-head .k{margin-left:auto;font-family:%(MONO)s;font-size:10px;color:var(--faint);letter-spacing:1.6px;text-transform:uppercase;text-align:right;}
.sec-intro{color:var(--muted);font-size:14.5px;font-style:italic;margin:-6px 0 20px;}

p{margin:0 0 15px;} .prose{font-size:16.5px;white-space:pre-wrap;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:20px 24px;margin:16px 0;color:var(--ink);}
.thread{max-width:760px;margin:10px auto 0;padding:26px 30px;border:1px solid var(--line);border-radius:4px;
background:var(--panel);font-size:17px;line-height:1.76;text-align:left;color:var(--ink);}
.thread .lead::first-letter{font-family:%(DISPLAY)s;font-size:3.1em;float:left;line-height:.82;padding:6px 10px 0 0;color:var(--accent);}
.callout{border-left:4px solid var(--accent);padding:12px 0 12px 18px;margin:20px 0;color:var(--accent2);background:var(--wash);font-style:normal;}
.highlight{border-left:4px solid var(--green);padding:12px 0 12px 18px;margin:20px 0;color:#255c38;background:rgba(61,125,82,.08);}
.warn{border-left:4px solid var(--yellow);padding:14px 0 14px 18px;margin:20px 0;color:#7a6212;background:rgba(168,134,31,.09);}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:700px){.grid2{grid-template-columns:1fr}}

table{width:100%%;border-collapse:collapse;font-size:13.5px;margin:12px 0;background:var(--panel);}
th,td{text-align:left;padding:9px 11px;border-bottom:1px solid var(--line-soft);vertical-align:top;color:var(--ink);}
th{font-family:%(MONO)s;font-size:10px;letter-spacing:.8px;text-transform:uppercase;color:#fff;background:var(--accent);font-weight:500;border-bottom:none;}
td.mono,th.mono{font-family:%(MONO)s;}
tr:nth-child(even) td{background:var(--panel2);}
.grid{font-family:%(MONO)s;font-size:12.5px;text-align:center;}
.grid th,.grid td{text-align:center;padding:6px 4px;}
.grid td.pl{text-align:left;font-family:%(SERIF)s;white-space:nowrap;color:var(--ink);}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:5px;}
.legend{font-size:11.5px;color:var(--muted);font-family:%(MONO)s;margin:8px 0 0;}
.legend b{color:var(--ink);font-weight:600;}
.pill{display:inline-block;font-family:%(MONO)s;font-size:10px;padding:2px 8px;border-radius:20px;
border:1px solid var(--line);color:var(--accent2);margin-right:4px;}
.dasha-now td{background:var(--soft) !important;}
.dasha-peak td{background:rgba(61,125,82,.13) !important;}
.hl-green td{background:rgba(61,125,82,.12) !important;}
.hl-amber td{background:rgba(168,134,31,.12) !important;}
.hl-red td{background:rgba(168,69,69,.09) !important;}

.planet-block{margin:14px 0;border:1px solid var(--line);border-radius:5px;overflow:hidden;background:var(--panel);}
.planet-head{display:flex;align-items:center;gap:12px;padding:13px 20px;background:rgba(138,109,47,.10);border-bottom:1px solid var(--line);}
.planet-head .gl{font-size:21px;color:var(--accent2);}
.planet-head .nm{font-family:%(DISPLAY)s;font-size:22px;color:var(--ink);}
.planet-head .vb{margin-left:auto;font-family:%(MONO)s;font-size:11px;color:var(--accent2);text-align:right;}
.planet-body{padding:6px 20px 14px;}
.planet-body h4{font-family:%(MONO)s;font-size:10px;letter-spacing:1.2px;text-transform:uppercase;color:var(--accent);margin:14px 0 5px;}
.planet-body p{font-size:14.5px;margin:0 0 6px;}
.acc-green{border-left:4px solid var(--green);}.acc-amber{border-left:4px solid var(--yellow);}.acc-red{border-left:4px solid var(--red);}

.tag{color:var(--green)} .tag.w{color:var(--red)} .tag.m{color:#8a6d10} .tag.b{color:var(--blue)} .tag.s{color:var(--saturn)}
.foot{margin-top:40px;padding-top:20px;border-top:2px solid var(--line);font-size:11.5px;color:var(--faint);
font-family:%(MONO)s;line-height:1.9;}

/* ── печать / PDF ─────────────────────────────────────────────────────────── */
@page{size:A4;margin:11mm 10mm 13mm 10mm;}
html,body{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important;}
section{break-before:page;page-break-before:always;}
section:first-of-type{break-before:auto;page-break-before:auto;}
.hero{break-after:page;page-break-after:always;}
.card,.biz-block,.planet-block,.thread,.callout,.highlight,.warn,.tablewrap,.chartwrap,.grid2>.card,.legend,svg{
break-inside:avoid;page-break-inside:avoid;}
tr{break-inside:avoid;page-break-inside:avoid;}
thead{display:table-header-group;}
.sec-head,h2,h3{break-after:avoid;page-break-after:avoid;}
.foot{break-before:page;page-break-before:always;}
""" % {
    "PAPER": theme.PAPER, "PANEL": theme.PANEL, "PANEL2": theme.PANEL2,
    "ACCENT": theme.ACCENT, "ACCENT2": theme.ACCENT2,
    "ACCENT_WASH": theme.ACCENT_WASH, "ACCENT_SOFT": theme.ACCENT_SOFT,
    "INK": theme.INK, "MUTED": theme.MUTED, "FAINT": theme.FAINT,
    "LINE": theme.LINE, "LINE_SOFT": theme.LINE_SOFT,
    "GREEN": theme.GREEN, "BLUE": theme.BLUE, "YELLOW": theme.YELLOW,
    "RED": theme.RED, "SATURN": theme.SATURN,
    "SERIF": theme.FONT_SERIF, "DISPLAY": theme.FONT_DISPLAY, "MONO": theme.FONT_MONO,
}

# No CDN font links: Google Fonts do not resolve offline or inside PDF renderers,
# which silently dropped the document to a default face on export.
HEAD = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Джйотиш-Альманах · __NAME__</title>
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
    # NB: not named `theme` — that would shadow the palette module imported above.
    houses={1:"«я», тело",2:"речь, деньги",3:"воля, усилие",4:"дом, покой",5:"дети, ум",
            6:"труд, здоровье",7:"партнёр, брак",8:"глубина, ресурсы",9:"судьба, вера",
            10:"карьера, дело",11:"доходы, круг",12:"уход, тайна"}
    rows=""
    for h in range(1,13):
        c,name=_q(sav[h],player[h])
        # keyed off the palette so a theme change cannot silently KeyError here
        cls={theme.GREEN:"",theme.BLUE:"b",theme.YELLOW:"m",theme.RED:"w"}[c]
        rows+=(f"<tr><td>{h} · {houses[h]}</td><td class='mono'>{sav[h]}</td>"
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
      <div class="thread"><p class="prose lead" style="margin:0">{esc(narrative.get('portrait',''))}</p></div></section>""")
    # 2 shodashavarga
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">2</div><h2>Сила дробных карт</h2></div>
      <h3 style="color:var(--accent);font-size:21px;margin:6px 0 4px">Сетка достоинств по 16 варгам</h3>
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
    col = theme.GREEN if pct>=0.72 else theme.ACCENT if pct>=0.5 else theme.RED
    large = 1 if (a0-a1) > math.pi else 0
    return f'''<svg viewBox="0 0 {W} 160" xmlns="http://www.w3.org/2000/svg" class="chart" style="max-width:360px">
      <path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 1 1 {xe:.1f} {ye:.1f}" fill="none" stroke="{theme.LINE}" stroke-width="14" stroke-linecap="round"/>
      <path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{col}" stroke-width="14" stroke-linecap="round"/>
      <text x="{cx}" y="{cy-6}" text-anchor="middle" fill="{col}" font-size="40" font-family="{theme.FONT_DISPLAY}" font-weight="600">{total:.0f}</text>
      <text x="{cx}" y="{cy+18}" text-anchor="middle" fill="{theme.MUTED}" font-size="13" font-family="{theme.FONT_MONO}">из {mx}</text>
    </svg>'''

def _kuta_rows(ak):
    out=""
    for r in ak["rows"]:
        pct=r["score"]/r["max"]
        col=theme.GREEN if pct>=0.75 else theme.ACCENT if pct>=0.4 else theme.RED
        out+=(f"<tr><td>{r['name']}</td>"
              f"<td class='mono' style='color:{col}'>{r['score']:g} / {r['max']}</td>"
              f"<td style='color:var(--muted);font-size:13px'>{r['meaning']}</td></tr>")
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
    if not items: return f"<p style='color:var(--muted)'>{guest}: нет планет в ключевых домах {host}.</p>"
    li="".join(f"<li><b>{o['planet']}</b> {guest} → <b>{o['house']}-й дом</b> {host} <span style='color:var(--muted)'>({o['theme']})</span></li>" for o in items)
    return f"<ul class='overlay'>{li}</ul>"

SYN_CSS = """
.cmp{margin:10px 0;} .cmp-head{display:flex;justify-content:space-between;font-family:%(MONO)s;font-size:11px;color:var(--accent);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;}
.cmp-row{display:grid;grid-template-columns:76px 1fr 34px 1fr 34px;align-items:center;gap:7px;margin-bottom:6px;font-size:13px;}
.cmp-l{color:var(--ink);} .cmp-v{color:var(--accent2);font-size:12px;text-align:center;}
.cmp-track{height:9px;border-radius:6px;background:var(--wash);overflow:hidden;display:flex;}
.cmp-track i{height:100%%;display:block;} .cmp-track i.a{background:%(BLUE)s;margin-left:auto;}
.cmp-track.r i.b{background:%(ACCENT)s;}
.overlay{list-style:none;padding:0;margin:6px 0;} .overlay li{padding:6px 0;border-bottom:1px solid var(--line-soft);font-size:14.5px;}
.names{display:flex;gap:18px;justify-content:center;font-family:%(MONO)s;font-size:12px;margin-top:6px;}
.names .a b{color:%(BLUE)s;} .names .b b{color:var(--accent);}
.tagset{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;}
.tagset span{font-family:%(MONO)s;font-size:11px;padding:3px 10px;border-radius:20px;border:1px solid var(--line);}
""" % {"MONO": theme.FONT_MONO, "BLUE": theme.BLUE, "ACCENT": theme.ACCENT}

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
      <p style="color:var(--accent);font-style:italic;margin-top:-6px">{verdict}</p></div>
      <div class="tablewrap"><table><thead><tr><th>Кута</th><th class="mono">Балл</th><th>Что показывает</th></tr></thead>
      <tbody>{_kuta_rows(ak)}</tbody></table></div>
      <p class="legend">Луна {na}: {syn['moon_a']['nak_name']} ({syn['moon_a']['sign_ru']}) · Луна {nb}: {syn['moon_b']['nak_name']} ({syn['moon_b']['sign_ru']})</p></section>""")
    # 2 field
    p.append(f"""<section><div class="sec-head"><div class="sec-num">2</div><h2>Сила ПОЛЯ — бинду по домам</h2></div>
      <div class="cmp-head"><span style="color:#2e567c">◧ {na}</span><span style="color:var(--accent)">{nb} ◧</span></div>
      {_cmp_bars(syn['field'],'a','b',na,nb)}</section>""")
    # 3 players
    p.append(f"""<section><div class="sec-head"><div class="sec-num">3</div><h2>Сила ИГРОКОВ — Вимшопака</h2></div>
      <div class="cmp-head"><span style="color:#2e567c">◧ {na}</span><span style="color:var(--accent)">{nb} ◧</span></div>
      {_cmp_bars(syn['players'],'a','b',na,nb)}</section>""")
    # 4 intersynastry
    p.append(f"""<section><div class="sec-head"><div class="sec-num">4</div><h2>Интерсинастрия — наложение карт</h2></div>
      <div class="card"><p style="margin:0 0 6px;color:var(--accent)"><b>Планеты {nb} на домах {na}</b></p>{_overlay_html(syn['overlay_ab'], na, nb)}</div>
      <div class="card"><p style="margin:0 0 6px;color:#2e567c"><b>Планеты {na} на домах {nb}</b></p>{_overlay_html(syn['overlay_ba'], nb, na)}</div>
      <p class="prose">{esc(narrative.get('intersynastry',''))}</p>
      <p class="legend">Даракарака (тема партнёра) — {na}: {syn['dara_a']['pl_ru']} · {nb}: {syn['dara_b']['pl_ru']}</p></section>""")
    # 5 contrasts
    def houses_tags(hs):
        return "".join(f"<span>дом {h}</span>" for h in hs) or "<span style='color:var(--muted)'>—</span>"
    p.append(f"""<section><div class="sec-head"><div class="sec-num">5</div><h2>Контрасты и дополнения</h2></div>
      <div class="card"><p style="margin:0 0 4px;color:#2f6340"><b>Дополнения</b> (один силён — другой опирается)</p><div class="tagset">{houses_tags(syn['complements'])}</div>
      <p style="margin:10px 0 4px;color:var(--blue)"><b>Общая сила</b> (оба сильны — синергия/соперничество)</p><div class="tagset">{houses_tags(syn['shared'])}</div>
      <p style="margin:10px 0 4px;color:#8c3838"><b>Зеркальная уязвимость</b> (оба слабы — беречь вместе)</p><div class="tagset">{houses_tags(syn['mirrors'])}</div></div>
      <p class="prose">{esc(narrative.get('contrasts',''))}</p></section>""")
    # 6 formula
    note=narrative.get("_note","")
    p.append(f"""<section><div class="sec-head"><div class="sec-num">6</div><h2>Формула пары</h2></div>
      <div class="thread"><p class="prose" style="margin:0">{esc(narrative.get('formula',''))}</p></div></section>
      <div class="foot">ДЖЙОТИШ · Совместимость · {na} × {nb}<br>
      Аштакута (Гуна Милан) 36 · SAV · Вимшопака · интерсинастрия · Swiss Ephemeris<br>
      Символический интерпретативный материал, не суждение о людях. {esc(note)}</div></div></body></html>""")
    return "".join(p)
