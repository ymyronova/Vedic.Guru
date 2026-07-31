# -*- coding: utf-8 -*-
"""Assemble the computed chart + SVGs + narrative into the full styled almanac HTML."""
import html as _h
import re
from datetime import timedelta

import theme
from charts import (natal_svg, vimshopaka_svg, sav_svg, bubble_svg, _q,
                    muntha_wheel_svg, monthly_axes_svg, dasha_gantt_svg,
                    stacked_bala_svg, saham_grid_svg, year_compare_svg,
                    months_overlay_svg)
from jyotish import PL_RU

# Tone-of-voice rule: every claim is written in plain language, followed by the
# chart parameter it rests on in parentheses. Setting those parentheses in the
# quiet .jy style keeps the sentence readable for someone who knows no jyotish,
# while leaving the term legible for cross-checking against the tables.
_JY_TERM = re.compile(r"\(([^()]{2,140})\)")

def _prose(text: str) -> str:
    """Escape narrative text, then style parenthesised jyotish terms."""
    return _JY_TERM.sub(r'<span class="jy">(\1)</span>', _h.escape(text or ""))

CSS = """
/* Vedic Guru brand book — 03 Color (P2 · locked).
   Paper ~70%% of any layout · Leaf for second surfaces and table zebra ·
   Ink for type and rules · Meridian ≤10%%, only on computed values and the
   primary action. No red/green pairs: nothing here is good or bad news. */
:root{--paper:%(PAPER)s;--panel:%(PANEL)s;--panel2:%(PANEL2)s;
--accent:%(ACCENT)s;--accent2:%(ACCENT2)s;--wash:%(ACCENT_WASH)s;--soft:%(ACCENT_SOFT)s;
--ink:%(INK)s;--body:%(BODY)s;--muted:%(MUTED)s;--faint:%(FAINT)s;
--line:%(LINE)s;--line-soft:%(LINE_SOFT)s;
--q4:%(Q_BOTH)s;--q3:%(Q_PLAYER)s;--q2:%(Q_FIELD)s;--q1:%(Q_NEITHER)s;
/* прежние семантические имена указывают на ту же шкалу, чтобы ни одна
   ссылка не осталась висящей и ни один «зелёный» не вернулся */
--green:%(Q_BOTH)s;--blue:%(Q_PLAYER)s;--yellow:%(Q_FIELD)s;--red:%(Q_NEITHER)s;
--saturn:%(SATURN)s;}
*{box-sizing:border-box}
/* 04 Typography: Helvetica Neue — body copy, navigation, buttons, forms.
   Body 17 / 1.65. Ink for structure, #454F4D for running text. */
body{margin:0;background:var(--paper);color:var(--body);
font-family:%(SANS)s;font-size:17px;line-height:1.65;-webkit-font-smoothing:antialiased;}
.wrap{max-width:940px;margin:0 auto;padding:0 24px 60px;}
/* Newsreader — headlines, manifesto, pull quotes, report titles. Light weights
   by brand (200/300/400); tight tracking at display sizes. */
h1,h2,h3,.disp{font-family:%(DISPLAY)s;font-weight:300;color:var(--ink);}
h2{font-size:34px;line-height:1.15;letter-spacing:-.015em;}
h3{font-size:22px;line-height:1.3;letter-spacing:0;}
/* Every computed value is monospaced AND tabular, so columns align and two
   reports can be compared without re-reading. */
.mono,td.mono,th.mono,.grid,.legend,.foot{font-family:%(MONO)s;
font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1;}
/* 05 Voice: plain language first, the term after — italic, one step lighter,
   never bold, never capitalised mid-sentence. */
.jy{color:var(--faint);font-size:.86em;font-style:italic;font-weight:400;}

.hero{padding:40px 0 26px;text-align:center;}
/* Eyebrow / data label — 10.5 / +16%% tracking, mono. */
.hero .eyebrow{font-family:%(MONO)s;font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);margin-bottom:10px;}
/* Manifesto — 56 / 1.05 / -2.5%%. Ink, not accent: Meridian is reserved for
   computed values and the primary action, capped at ~10%% of the layout. */
.hero h1{font-size:clamp(38px,7.5vw,56px);line-height:1.05;letter-spacing:-.025em;
margin:.1em 0;font-weight:200;color:var(--ink);}
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
/* Выноски различаются насыщенностью подложки и толщиной линии, а не цветом:
   ни один блок отчёта не является «хорошей» или «плохой» новостью. */
.highlight{border-left:4px solid var(--accent);padding:12px 0 12px 18px;margin:20px 0;color:var(--ink);background:var(--wash);}
.warn{border-left:4px solid var(--q1);padding:14px 0 14px 18px;margin:20px 0;color:var(--ink);background:var(--panel2);}
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
/* Подсветка строк — та же шкала интенсивности, что и у квадрантов. */
.dasha-peak td{background:var(--wash) !important;}
.hl-green td{background:var(--wash) !important;}
.hl-amber td{background:var(--panel2) !important;}
.hl-red td{background:var(--panel2) !important;}

.planet-block{margin:14px 0;border:1px solid var(--line);border-radius:5px;overflow:hidden;background:var(--panel);}
.planet-head{display:flex;align-items:center;gap:12px;padding:13px 20px;background:var(--wash);border-bottom:1px solid var(--line);}
.planet-head .gl{font-size:21px;color:var(--accent2);}
.planet-head .nm{font-family:%(DISPLAY)s;font-size:22px;color:var(--ink);}
.planet-head .vb{margin-left:auto;font-family:%(MONO)s;font-size:11px;color:var(--accent2);text-align:right;}
.planet-body{padding:6px 20px 14px;}
.planet-body h4{font-family:%(MONO)s;font-size:10px;letter-spacing:1.2px;text-transform:uppercase;color:var(--accent);margin:14px 0 5px;}
.planet-body p{font-size:14.5px;margin:0 0 6px;}
.acc-green{border-left:4px solid var(--green);}.acc-amber{border-left:4px solid var(--yellow);}.acc-red{border-left:4px solid var(--red);}

/* Сила читается интенсивностью одного тона, а не сменой цвета: бренд-бук
   запрещает пары «зелёный — красный», потому что ни один дом не является
   хорошей или плохой новостью. */
.tag{font-family:%(MONO)s;font-size:11px;letter-spacing:.4px;}
.tag.q4{color:%(Q_BOTH)s} .tag.q3{color:%(Q_PLAYER)s}
.tag.q2{color:%(Q_FIELD)s} .tag.q1{color:%(Q_NEITHER)s}
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

/* ---- годовой слой (Варшапхала) ---- */
.part-head{margin:0 0 18px;padding:16px 0 12px;border-top:2px solid var(--accent);
  border-bottom:1px solid var(--line);}
.part-kicker{font-family:%(MONO)s;font-size:11px;letter-spacing:2.5px;
  text-transform:uppercase;color:var(--accent);margin:0 0 4px;}
.part-head h2{margin:0;font-size:30px;}
.part-head .sub{color:var(--muted);font-size:13.5px;margin-top:5px;}

/* Ключевые факты: рамка перед основным текстом части, одна строка —
   одно утверждение, чтобы блок читался без прокрутки. */
.facts{border:1px solid var(--accent);border-radius:6px;background:var(--wash);
  padding:14px 18px;margin:0 0 22px;}
.facts dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:0;}
.facts dt{font-family:%(MONO)s;font-size:11px;letter-spacing:.6px;
  text-transform:uppercase;color:var(--accent2);white-space:nowrap;padding-top:2px;}
.facts dd{margin:0;color:var(--ink);font-size:14px;line-height:1.45;}

/* «Влияние на жизнь» — три-четыре строки после КАЖДОГО раздела: перевод
   технического содержания в практическое следствие, а не пересказ таблицы. */
.impact{border-left:3px solid var(--accent);background:var(--panel2);
  padding:11px 15px;margin:14px 0 0;border-radius:0 4px 4px 0;}
.impact .lbl{font-family:%(MONO)s;font-size:10px;letter-spacing:1.6px;
  text-transform:uppercase;color:var(--accent2);display:block;margin-bottom:4px;}
.impact p{margin:0;font-size:14px;line-height:1.55;color:var(--body);}

/* One-pager: год на одном экране, читаемый в отрыве от документа. */
.onepager{border:1px solid var(--line);border-radius:6px;padding:18px 20px;
  background:var(--panel);}
.onepager h3{margin:0 0 12px;font-size:20px;color:var(--accent2);}
.op-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.op-col h4{margin:0 0 6px;font-size:13px;font-family:%(MONO)s;letter-spacing:1px;
  text-transform:uppercase;color:var(--faint);font-weight:500;}
.op-col ul{margin:0;padding-left:17px;}
.op-col li{font-size:13.5px;line-height:1.5;color:var(--body);margin-bottom:4px;}
.op-formula{margin-top:16px;padding-top:12px;border-top:1px solid var(--line-soft);
  font-family:%(DISPLAY)s;font-size:17px;line-height:1.4;color:var(--ink);}
@media(max-width:640px){.op-grid{grid-template-columns:1fr}}

.mtable td.num{font-family:%(MONO)s;text-align:right;white-space:nowrap;}
.bar-cell{display:inline-block;height:8px;border-radius:2px;background:var(--q3);
  vertical-align:middle;}
.sign-pos{color:var(--q4);} .sign-neg{color:var(--q1);}
.yoga-row td:first-child{width:34%%;}
.unverified{color:var(--faint);font-size:11px;font-family:%(MONO)s;}
""" % {
    "PAPER": theme.PAPER, "PANEL": theme.PANEL, "PANEL2": theme.PANEL2,
    "ACCENT": theme.ACCENT, "ACCENT2": theme.ACCENT2,
    "ACCENT_WASH": theme.ACCENT_WASH, "ACCENT_SOFT": theme.ACCENT_SOFT,
    "INK": theme.INK, "BODY": theme.BODY, "MUTED": theme.MUTED, "FAINT": theme.FAINT,
    "LINE": theme.LINE, "LINE_SOFT": theme.LINE_SOFT,
    "Q_BOTH": theme.Q_BOTH, "Q_PLAYER": theme.Q_PLAYER,
    "Q_FIELD": theme.Q_FIELD, "Q_NEITHER": theme.Q_NEITHER,
    "SATURN": theme.SATURN,
    "SERIF": theme.FONT_SERIF, "SANS": theme.FONT_SANS,
    "DISPLAY": theme.FONT_DISPLAY, "MONO": theme.FONT_MONO,
}

# Brand typefaces come from Google Fonts for screen, but every stack keeps a
# local fallback: the PDF is rendered by WeasyPrint inside the container, where
# no webfont is fetched, and a missing fallback would print Cyrillic as boxes.
HEAD = ("""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Джйотиш-Альманах · __NAME__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="%s" rel="stylesheet">
<style>%s</style></head><body><div class="wrap">""" % (theme.GOOGLE_FONTS, CSS))

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
        cls={theme.Q_BOTH:"q4",theme.Q_PLAYER:"q3",
             theme.Q_FIELD:"q2",theme.Q_NEITHER:"q1"}[c]
        rows+=(f"<tr><td>{h} · {houses[h]}</td><td class='mono'>{sav[h]}</td>"
               f"<td class='mono'>{player[h]:.1f}</td><td><span class='tag {cls}'>{name}</span></td></tr>")
    return rows

def _qa_section(qa, num):
    """Раздел «Ваши вопросы» — только то, что человек сам выбрал добавить.

    Вопросы включаются в документ, поэтому попадают и в PDF, и в скачанный
    HTML: разговор становится частью отчёта, а не остаётся в интерфейсе.
    """
    if not qa:
        return ""
    esc = _h.escape
    items = ""
    for pair in qa:
        q = str(pair.get("q", "")).strip()
        a = str(pair.get("a", "")).strip()
        if not q or not a:
            continue
        items += (f"<div class='card'><p style='margin:0 0 8px'>"
                  f"<b>{esc(q)}</b></p>"
                  f"<p class='prose' style='margin:0'>{_prose(a)}</p></div>")
    if not items:
        return ""
    return (f"""<section><div class="sec-head"><div class="sec-num">{num}</div>
      <h2>Ваши вопросы</h2></div>
      <p class="sec-intro">Заданы вами после прочтения альманаха; ответы опираются
      на тот же расчёт.</p>{items}</section>""")


# ============================================================================
# Годовой слой: части по годам + сквозное сравнение
# ============================================================================
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
NATAL_SECTIONS = 4


def _next_num(chart):
    """Номер следующего раздела после всех годовых частей и сравнения."""
    n = NATAL_SECTIONS
    parts = chart.get("varsha") or []
    if parts:
        n += 1                      # блок сравнения идёт одним разделом
    return n + 1


def _impact(text, fallback):
    """Блок «Влияние на жизнь» — после каждого раздела без исключений.

    Пустым он быть не может: если модель не дала текста, следствие собирается
    из самих данных. Раздел без ответа на «и что мне с этим делать» — это
    таблица, оставленная читателю на самостоятельный разбор.
    """
    body = (text or "").strip() or fallback
    return (f'<div class="impact"><span class="lbl">Влияние на жизнь</span>'
            f'<p>{_prose(body)}</p></div>')


def _facts_box(part):
    """Ключевые факты года: одна строка — одно утверждение, один экран."""
    esc = _h.escape
    v = part["varshesha"]["winner"]
    mun = part["muntha"]
    best = sorted(part["months"], key=lambda m: -m["valence"])[:2]
    worst = min(part["months"], key=lambda m: m["valence"])
    strongest = max(part["pancha"].items(), key=lambda kv: kv[1]["total"])
    rare = [y["name"] for y in part["tajika"]["yogas"]
            if y["present"] and y["verdict"] == "хорошо"][:3]
    risk = [y["name"] for y in part["tajika"]["yogas"]
            if y["present"] and y["verdict"] == "трудно"][:3]
    stell = _stelliums(part)

    rows = [
        ("Варша-Лагна", f'{part["lagna_sign_ru"]} {part["lagna_dms"]} · '
                        f'упр. {PL_RU[part["lagna_lord"]]}'),
        ("Варшеша", f'{v["planet_ru"]} ({v["bala"]:.1f} из 20) — {v["role"]}'),
        ("Мунтха", f'{mun["sign_ru"]} — {mun["house"]}-й дом'),
        ("Стеллиум", stell or "нет скоплений — планеты разведены по домам"),
        ("Сильнейшая", f'{PL_RU[strongest[0]]} {strongest[1]["total"]:.1f} из 20'),
        ("Опорные связи", ", ".join(rare) if rare else "выраженных нет"),
        ("Что беречь", ", ".join(risk) if risk else "тяжёлых связей нет"),
        ("Лучшие месяцы", ", ".join(m["label"] for m in best)),
        ("Трудный месяц", worst["label"]),
    ]
    dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(val)}</dd>" for k, val in rows)
    return f'<div class="facts"><dl>{dl}</dl></div>'


def _stelliums(part):
    by_house = {}
    for p in part["planets"]:
        if p["code"] in ("Ra", "Ke"):
            continue
        by_house.setdefault(p["house"], []).append(p["name"])
    out = [f'{", ".join(v)} — все в {h}-м доме'
           for h, v in sorted(by_house.items()) if len(v) >= 3]
    return "; ".join(out)


def _year_chart_table(part):
    rows = ""
    for p in part["planets"]:
        rules = ", ".join(f"{h}-й" for h in p["rules"]) or "—"
        rows += (f'<tr><td>{_h.escape(p["name"])}</td>'
                 f'<td class="mono">{_h.escape(p["pos"])}</td>'
                 f'<td class="mono">{p["house"]}</td>'
                 f'<td class="mono">{rules}</td>'
                 f'<td>{_h.escape(p["dignity_ru"])}</td></tr>')
    return (f'<div class="tablewrap"><table><thead><tr><th>Планета</th>'
            f'<th class="mono">Долгота</th><th class="mono">Дом</th>'
            f'<th class="mono">Управляет</th><th>Положение</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def _tajika_table(part):
    """16 Таджака-йог. Термин уходит в скобки, смысл стоит первым."""
    rows = ""
    for y in part["tajika"]["yogas"]:
        mark = "есть" if y["present"] else "нет"
        cls = "" if y["present"] else ' style="opacity:.5"'
        # Смысл первым, термин следом в скобках — конвенция .jy. Сырое название
        # в заголовке или колонке её нарушает, поэтому имени отдельной колонки нет.
        claim = "{} ({})".format(y["meaning"], y["name"])
        rows += (f'<tr class="yoga-row"{cls}>'
                 f'<td>{_prose(claim)}</td>'
                 f'<td class="mono">{mark}</td>'
                 f'<td>{_h.escape(y["condition"])}</td>'
                 f'<td>{_h.escape(y["evidence"])}</td></tr>')
    return (f'<div class="tablewrap"><table><thead><tr><th>Что это значит</th>'
            f'<th class="mono">В карте</th><th>Техническое условие</th>'
            f'<th>Основание</th></tr></thead><tbody>{rows}</tbody></table></div>')


def _saham_table(part):
    """36 сахамов по месяцам активации."""
    rows = ""
    for m in part["months"]:
        for s in m["saham_records"]:
            risky = any(w in s["meaning"] for w in ("риск", "беречь", "осторожность"))
            status = "беречь" if risky else "поддержан"
            flag = ('<span class="unverified"> формула не подтверждена</span>'
                    if not s.get("verified", True) else "")
            rows += (f'<tr><td class="mono">{_h.escape(m["label"])}</td>'
                     f'<td>{_h.escape(s["name"])}{flag}</td>'
                     f'<td class="mono">{_h.escape(s["pos"])}</td>'
                     f'<td class="mono">{s["house"]}</td>'
                     f'<td>{_h.escape(s["meaning"])}</td>'
                     f'<td>{status}</td></tr>')
    return (f'<div class="tablewrap"><table><thead><tr><th class="mono">Мес.</th>'
            f'<th>Тема</th><th class="mono">Положение</th><th class="mono">Дом</th>'
            f'<th>Что это в жизни</th><th>Статус</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def _month_table(part):
    """Двенадцать строк — по одной на месяц года."""
    rows = ""
    for m in part["months"]:
        occ = ", ".join(m["occupants_ru"]) or "пусто"
        sign_cls = "sign-pos" if m["valence"] >= 0 else "sign-neg"
        bar = int(max(m["salience"], 0) * 7)
        todo = ("укреплять и вкладываться" if m["valence"] >= 1.5
                else "держать ровный ход" if m["valence"] >= 0
                else "не начинать нового, беречь" if m["valence"] >= -1.5
                else "переждать, закрывать хвосты")
        rows += (f'<tr><td class="mono">{_h.escape(m["label"])}</td>'
                 f'<td class="mono">{_h.escape(m["sign_ru"])} · {m["house"]}-й</td>'
                 f'<td>{_h.escape(occ)}</td>'
                 f'<td class="num"><span class="bar-cell" style="width:{bar}px"></span> '
                 f'{m["salience"]:.1f}</td>'
                 f'<td class="num {sign_cls}">{m["valence"]:+.1f}</td>'
                 f'<td>{_h.escape(", ".join(m["sahams"][:3]) or "—")}</td>'
                 f'<td>{todo}</td></tr>')
    return (f'<div class="tablewrap"><table class="mtable"><thead><tr>'
            f'<th class="mono">Месяц</th><th class="mono">Знак · дом</th>'
            f'<th>Планеты</th><th class="mono">Громкость денег</th>'
            f'<th class="mono">Знак исхода</th><th>Темы месяца</th>'
            f'<th>Что делать</th></tr></thead><tbody>{rows}</tbody></table></div>')


def _dasha_tables(part):
    out = ""
    for name, segs in part["dashas"].items():
        rows = "".join(
            f'<tr><td>{_h.escape(str(s["lord"]))}</td>'
            f'<td class="mono">{s["start"]:%d.%m.%Y}</td>'
            f'<td class="mono">{s["end"]:%d.%m.%Y}</td>'
            f'<td class="num">{s["days"]:.0f}</td></tr>' for s in segs)
        out += (f'<h3 style="font-size:16px;margin:14px 0 6px;color:var(--accent2)">'
                f'{_h.escape(name)}</h3>'
                f'<div class="tablewrap"><table><thead><tr><th>Управитель</th>'
                f'<th class="mono">С</th><th class="mono">По</th>'
                f'<th class="num">Дней</th></tr></thead><tbody>{rows}</tbody>'
                f'</table></div>')
    return out


def _onepager(part, ny):
    """Год на одном экране — раздел, который читается в отрыве от документа."""
    esc = _h.escape
    v = part["varshesha"]["winner"]
    mun = part["muntha"]
    months = part["months"]
    best = sorted(months, key=lambda m: -m["valence"])[:3]
    worst = sorted(months, key=lambda m: m["valence"])[:3]
    loud = max(months, key=lambda m: m["salience"])

    focus = ny.get("focus") or [
        f'Тема года заявлена {mun["house"]}-м домом — {mun["sign_ru"]}',
        f'Опора года — {v["planet_ru"]}, сила {v["bala"]:.1f} из 20',
        f'Денежная тема громче всего звучит в {loud["label"]}',
    ]
    care = ny.get("care") or [
        f'{worst[0]["label"]} — знак исхода {worst[0]["valence"]:+.1f}',
        f'{worst[1]["label"]} — знак исхода {worst[1]["valence"]:+.1f}',
        "Громкая тема при отрицательном знаке — не повод действовать быстрее",
    ]
    frame = [
        ("Варша-Лагна", f'{part["lagna_sign_ru"]} {part["lagna_dms"]}'),
        ("Управитель года", f'{v["planet_ru"]} · {v["bala"]:.1f}/20'),
        ("Мунтха", f'{mun["sign_ru"]} · {mun["house"]}-й дом'),
        ("Вход в год", f'{part["pravesh"]["local"]:%d.%m.%Y %H:%M}'),
        ("Лучшие месяцы", ", ".join(m["label"] for m in best)),
        ("Трудные месяцы", ", ".join(m["label"] for m in worst)),
    ]
    frame_rows = "".join(
        f'<tr><td>{esc(k)}</td><td class="mono">{esc(val)}</td></tr>'
        for k, val in frame)
    arc = " · ".join(f'{m["label"]} {m["valence"]:+.1f}' for m in months)
    formula = ny.get("formula") or (
        f'Год держится на {v["planet_ru"]} и говорит о теме {mun["house"]}-го дома.')

    spheres = ny.get("spheres") or []
    sph_html = ""
    if spheres:
        sph_html = ("<h4>Сферы жизни</h4><ul>" + "".join(
            f'<li>{_prose(str(s))}</li>' for s in spheres) + "</ul>")

    return f"""<div class="onepager">
      <h3>Год на одном экране</h3>
      <div class="tablewrap"><table><tbody>{frame_rows}</tbody></table></div>
      <div class="op-grid" style="margin-top:14px">
        <div class="op-col"><h4>Три фокуса</h4><ul>
          {"".join(f"<li>{_prose(str(x))}</li>" for x in focus[:3])}</ul>{sph_html}</div>
        <div class="op-col"><h4>Три зоны осторожности</h4><ul>
          {"".join(f"<li>{_prose(str(x))}</li>" for x in care[:3])}</ul></div>
      </div>
      <p class="legend" style="margin-top:12px">Дуга года по месяцам (знак исхода): {esc(arc)}</p>
      <div class="op-formula">{_prose(formula)}</div>
    </div>"""


def _annual_parts(chart, narrative):
    """Годовые части: по одиннадцать разделов на каждую."""
    parts = chart.get("varsha") or []
    if not parts:
        return ""
    years_text = narrative.get("years") or []
    out = []
    for i, part in enumerate(parts):
        ny = years_text[i] if i < len(years_text) else {}
        imp = ny.get("impacts") or {}
        mun = part["muntha"]
        v = part["varshesha"]["winner"]
        pv_rows = [(PL_RU[p], part["pancha"][p]["parts"]) for p in part["pancha"]]
        hb_rows = [(PL_RU[p], part["harsha"][p]["parts"]) for p in part["harsha"]]
        loud = max(part["months"], key=lambda m: m["salience"])
        worst = min(part["months"], key=lambda m: m["valence"])

        body = [f"""<div class="part-head">
          <p class="part-kicker">Часть {ROMAN[i] if i < len(ROMAN) else i + 1} · год {_h.escape(part["label"])}</p>
          <h2>{_h.escape(part["label"])} — возраст {part["age"]}</h2>
          <div class="sub">Вход в год: {part["pravesh"]["local"]:%d.%m.%Y %H:%M} ·
            {_h.escape(part.get("place") or "")} · карта
            {"дневная" if part["is_day"] else "ночная"}</div></div>"""]

        body.append(_facts_box(part))
        if ny.get("thread"):
            body.append(f'<div class="thread"><p class="prose lead" style="margin:0">'
                        f'{_prose(ny["thread"])}</p></div>')

        body.append("<h3>Годовая карта</h3>" + _year_chart_table(part))
        body.append(_impact(imp.get("chart"),
                            f'Год разложен по домам так: тяжесть смещена туда, где стоят '
                            f'планеты, и именно эти области будут требовать внимания.'))

        body.append("<h3>Тема года</h3>"
                    f'<p class="prose">Тематический дом года — {mun["house"]}-й '
                    f'({_h.escape(mun["sign_ru"])}): точка, которая продвигается на один '
                    f'знак за прожитый год (Мунтха). Её управитель — '
                    f'{_h.escape(mun["lord_ru"])}.</p>'
                    f'<div class="card">{muntha_wheel_svg(part["months"], mun["sign"], part["lagna_sign"])}</div>')
        body.append(_impact(imp.get("muntha"),
                            f'Что бы ни происходило в этом году, оно будет собираться вокруг '
                            f'темы {mun["house"]}-го дома — туда стоит вкладывать, а не спорить с этим.'))

        cand = "".join(
            f'<tr><td>{_h.escape(c["role"])}</td><td>{_h.escape(c["planet_ru"])}</td>'
            f'<td class="num">{c["bala"]:.1f}</td></tr>'
            for c in part["varshesha"]["candidates"])
        body.append(f"""<h3>Управитель года и силы</h3>
          <p class="prose">Управителем года становится сильнейший из пяти претендентов —
          {_h.escape(v["planet_ru"])}, {v["bala"]:.1f} из 20 (Варшеша).</p>
          <div class="tablewrap"><table><thead><tr><th>Претендент</th><th>Планета</th>
          <th class="num">Сила</th></tr></thead><tbody>{cand}</tbody></table></div>
          <div class="card">{stacked_bala_svg(pv_rows, 20, "")}
            <p class="legend" style="text-align:center">Из чего собрана сила планеты (Панча-Варгия, из 20)</p></div>
          <div class="card">{stacked_bala_svg(hb_rows, 25, "")}
            <p class="legend" style="text-align:center">Достоинства по пяти условиям (Харша-бала)</p></div>""")
        body.append(_impact(imp.get("varshesha"),
                            f'{v["planet_ru"]} задаёт тон году: к чему эта планета '
                            f'расположена, то в этом году идёт легче.'))

        body.append("<h3>Связи года</h3>" + _tajika_table(part))
        body.append(_impact(imp.get("tajika"),
                            'Связи на подходе — то, что ещё созревает и требует участия; '
                            'распавшиеся — то, что уйдёт само, даже если тратить силы.'))

        body.append(f"""<h3>Пять годовых шкал</h3>
          <p class="prose">Пять систем делят один и тот же год по-разному, и совпадение
          тяжёлого управителя сразу в нескольких — более веское, чем в одной.</p>
          <div class="card">{dasha_gantt_svg(part["dashas"], part["pravesh"]["local"],
                                             part["pravesh"]["local"] + _td(part["length_days"]))}</div>
          {_dasha_tables(part)}""")
        body.append(_impact(imp.get("dashas"),
                            'Смотреть стоит туда, где несколько шкал сходятся на одном '
                            'управителе: там год меняет характер заметнее всего.'))

        body.append("<h3>Темы года по месяцам</h3>" + _saham_table(part) +
                    f'<div class="card">{saham_grid_svg(part["months"])}'
                    f'<p class="legend" style="text-align:center">Когда какая тема включается '
                    f'(чувствительные точки года — сахамы)</p></div>')
        body.append(_impact(imp.get("sahams"),
                            'Тема включается в свой месяц — это подсказка, когда именно '
                            'заниматься вопросом, а не заниматься им весь год подряд.'))

        body.append("<h3>Помесячная таблица</h3>" + _month_table(part))
        body.append(_impact(imp.get("months"),
                            f'Громче всего денежная тема звучит в {loud["label"]}, '
                            f'а труднее всего складывается {worst["label"]}.'))

        body.append(f"""<h3>Две оси года</h3>
          <p class="prose">Это две разные величины, а не одна: столбцы — насколько громко
          звучит денежная тема, ломаная — знак исхода. Громко и в минусе — не то же самое,
          что тихо.</p>
          <div class="card">{monthly_axes_svg(part["months"])}</div>""")
        body.append(_impact(imp.get("axes"),
                            'Месяц с громкой темой и отрицательным знаком — не сигнал '
                            'ускоряться, а сигнал не подписывать нового.'))

        body.append(_onepager(part, ny))
        body.append(_impact(imp.get("onepager"),
                            'Если из года запомнить одно — пусть это будет формула выше.'))

        out.append(f'<section>{"".join(body)}</section>')
    return "".join(out)


def _td(days):
    return timedelta(days=days)


def _compare_block(chart, narrative):
    """Сквозное сравнение: тренд, которого не видно ни в одной отдельной части."""
    parts = chart.get("varsha") or []
    if len(parts) < 2:
        return ""
    nc = (narrative.get("compare") or {})
    labels = [p["label"] for p in parts]

    rows = "".join(
        f'<tr><td>{_h.escape(k)}</td>' +
        "".join(f'<td class="num">{_h.escape(str(val))}</td>' for val in vals) +
        "</tr>"
        for k, vals in _compare_rows(parts).items())
    head = "".join(f'<th class="mono">{_h.escape(l)}</th>' for l in labels)

    series = {
        "Сила управителя года": [round(p["varshesha"]["winner"]["bala"], 1) for p in parts],
        "Опорных связей": [sum(1 for y in p["tajika"]["yogas"]
                               if y["present"] and y["verdict"] == "хорошо") for p in parts],
        "Тяжёлых связей": [sum(1 for y in p["tajika"]["yogas"]
                               if y["present"] and y["verdict"] == "трудно") for p in parts],
        "Средняя громкость денег": [round(sum(m["salience"] for m in p["months"]) / 12, 1)
                                    for p in parts],
    }
    money = {
        "Сумма знака исхода": [round(sum(m["valence"] for m in p["months"]), 1) for p in parts],
        "Пик громкости": [round(max(m["salience"] for m in p["months"]), 1) for p in parts],
    }
    overlay = [(p["label"], [m["valence"] for m in p["months"]]) for p in parts]

    return f"""<section>
      <div class="sec-head"><div class="sec-num">{NATAL_SECTIONS + 1}</div>
        <h2>Сравнение лет</h2></div>
      <p class="prose">Каждая часть выше самодостаточна, и именно поэтому тренд между
      годами в них не виден. Здесь годы стоят рядом на одной шкале.</p>
      <div class="tablewrap"><table><thead><tr><th>Параметр</th>{head}</tr></thead>
        <tbody>{rows}</tbody></table></div>
      {_impact(nc.get("params"), "Сравнивать стоит не абсолютные числа, а направление: "
                                 "что растёт от года к году, а что убывает.")}
      <h3>Параметры по годам</h3>
      <div class="card">{year_compare_svg(series, labels, "")}</div>
      {_impact(nc.get("trend"), "Год с сильным управителем и малым числом тяжёлых связей "
                                "проще для крупных решений, чем год с обратным набором.")}
      <h3>Финансовый разрез</h3>
      <div class="card">{year_compare_svg(money, labels, "")}</div>
      {_impact(nc.get("money"), "Громкость и знак исхода снова разведены: год может быть "
                                "шумным по деньгам и при этом убыточным по знаку.")}
      <h3>Единая шкала месяцев</h3>
      <div class="card">{months_overlay_svg(overlay)}</div>
      {_impact(nc.get("months"), "Наложение показывает, повторяется ли трудный месяц из года "
                                 "в год или это разовое совпадение.")}
    </section>"""


def _compare_rows(parts):
    out = {}
    out["Варша-Лагна"] = [p["lagna_sign_ru"] for p in parts]
    out["Управитель года"] = [p["varshesha"]["winner"]["planet_ru"] for p in parts]
    out["Сила управителя"] = [f'{p["varshesha"]["winner"]["bala"]:.1f}' for p in parts]
    out["Мунтха · дом"] = [f'{p["muntha"]["sign_ru"]} · {p["muntha"]["house"]}-й'
                           for p in parts]
    out["Лучший месяц"] = [max(p["months"], key=lambda m: m["valence"])["label"]
                           for p in parts]
    out["Трудный месяц"] = [min(p["months"], key=lambda m: m["valence"])["label"]
                            for p in parts]
    out["Опорных связей"] = [sum(1 for y in p["tajika"]["yogas"]
                                 if y["present"] and y["verdict"] == "хорошо")
                             for p in parts]
    out["Тяжёлых связей"] = [sum(1 for y in p["tajika"]["yogas"]
                                 if y["present"] and y["verdict"] == "трудно")
                             for p in parts]
    return out


def render_almanac(name, birth_meta, chart, narrative, focus=None, qa=None):
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
      {f'<div class="focus-badge">Фокус: {esc(focus)}</div>' if focus else ''}
      <div class="chartwrap">{natal_svg(chart)}</div></div>""")
    # 1 portrait
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">1</div><h2>Портрет одной нитью</h2></div>
      <div class="thread"><p class="prose lead" style="margin:0">{_prose(narrative.get('portrait',''))}</p></div></section>""")
    # 2 yogas
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">2</div><h2>Ключевые йоги</h2></div>
      <p class="prose">{_prose(narrative.get('yogas',''))}</p>{_yoga_cards(chart)}</section>""")
    # 3 dasha
    ad=next((x for x in chart["antardashas"] if x["current"]),None)
    ad_line=(f"Сейчас: <b>{chart['current_dasha']['lord_ru']} · {ad['lord_ru']}</b> "
             f"(до {ad['end'].year}.{ad['end'].month:02d})." if ad else "")
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">3</div><h2>Вимшоттари — дуга жизни</h2></div>
      <div class="tablewrap"><table><thead><tr><th>Махадаша</th><th class="mono">Годы</th><th class="mono">Возраст</th></tr></thead>
      <tbody>{_dasha_rows(chart)}</tbody></table></div>
      <div class="callout">{ad_line}</div>
      <p class="prose">{_prose(narrative.get('dasha',''))}</p></section>""")
    # 4 integral — сюда же переехал итоговый Вимшопака-балл: он и есть ось
    # «игрок» на этой диаграмме, а развёрнутая сетка достоинств по 16 варгам
    # убрана как отдельная таблица.
    parts.append(f"""<section><div class="sec-head"><div class="sec-num">4</div><h2>Интегральная карта судьбы</h2></div>
      <p>Каждый дом — это <b>поле</b> (бинду) и <b>игрок</b> (Вимшопака держателя). Ось X — сила поля, ось Y — сила игрока.</p>
      <div class="card" style="padding:14px">{bubble}</div>
      <div class="tablewrap"><table><thead><tr><th>Дом · сфера</th><th class="mono">Поле</th><th class="mono">Игрок</th><th>Тип</th></tr></thead>
      <tbody>{_section5_table(chart,player)}</tbody></table></div>
      <div class="card">{vimshopaka_svg(chart)}<p class="legend" style="text-align:center">Вимшопака-балл (из 20) — сила игрока</p></div>
      <div class="card">{sav_svg(chart)}<p class="legend" style="text-align:center">Бинду по домам — сила поля · ось X: номер дома</p></div>
      <p class="prose">{_prose(narrative.get('shodashavarga',''))}</p>
      <div class="card"><p class="prose" style="margin:0">{_prose(narrative.get('integral',''))}</p></div></section>""")
    parts.append(_annual_parts(chart, narrative))
    parts.append(_compare_block(chart, narrative))
    parts.append(_qa_section(qa, _next_num(chart)))
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
      <div class="cmp-head"><span style="color:var(--q3)">◧ {na}</span><span style="color:var(--accent)">{nb} ◧</span></div>
      {_cmp_bars(syn['field'],'a','b',na,nb)}</section>""")
    # 3 players
    p.append(f"""<section><div class="sec-head"><div class="sec-num">3</div><h2>Сила ИГРОКОВ — Вимшопака</h2></div>
      <div class="cmp-head"><span style="color:var(--q3)">◧ {na}</span><span style="color:var(--accent)">{nb} ◧</span></div>
      {_cmp_bars(syn['players'],'a','b',na,nb)}</section>""")
    # 4 intersynastry
    p.append(f"""<section><div class="sec-head"><div class="sec-num">4</div><h2>Интерсинастрия — наложение карт</h2></div>
      <div class="card"><p style="margin:0 0 6px;color:var(--accent)"><b>Планеты {nb} на домах {na}</b></p>{_overlay_html(syn['overlay_ab'], na, nb)}</div>
      <div class="card"><p style="margin:0 0 6px;color:var(--q3)"><b>Планеты {na} на домах {nb}</b></p>{_overlay_html(syn['overlay_ba'], nb, na)}</div>
      <p class="prose">{_prose(narrative.get('intersynastry',''))}</p>
      <p class="legend">Даракарака (тема партнёра) — {na}: {syn['dara_a']['pl_ru']} · {nb}: {syn['dara_b']['pl_ru']}</p></section>""")
    # 5 contrasts
    def houses_tags(hs):
        return "".join(f"<span>дом {h}</span>" for h in hs) or "<span style='color:var(--muted)'>—</span>"
    p.append(f"""<section><div class="sec-head"><div class="sec-num">5</div><h2>Контрасты и дополнения</h2></div>
      <div class="card"><p style="margin:0 0 4px;color:var(--q4)"><b>Дополнения</b> (один силён — другой опирается)</p><div class="tagset">{houses_tags(syn['complements'])}</div>
      <p style="margin:10px 0 4px;color:var(--blue)"><b>Общая сила</b> (оба сильны — синергия/соперничество)</p><div class="tagset">{houses_tags(syn['shared'])}</div>
      <p style="margin:10px 0 4px;color:var(--q1)"><b>Зеркальная уязвимость</b> (оба слабы — беречь вместе)</p><div class="tagset">{houses_tags(syn['mirrors'])}</div></div>
      <p class="prose">{_prose(narrative.get('contrasts',''))}</p></section>""")
    # 6 formula
    note=narrative.get("_note","")
    p.append(f"""<section><div class="sec-head"><div class="sec-num">6</div><h2>Формула пары</h2></div>
      <div class="thread"><p class="prose" style="margin:0">{_prose(narrative.get('formula',''))}</p></div></section>
      <div class="foot">ДЖЙОТИШ · Совместимость · {na} × {nb}<br>
      Аштакута (Гуна Милан) 36 · SAV · Вимшопака · интерсинастрия · Swiss Ephemeris<br>
      Символический интерпретативный материал, не суждение о людях. {esc(note)}</div></div></body></html>""")
    return "".join(p)
