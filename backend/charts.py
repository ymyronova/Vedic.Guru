# -*- coding: utf-8 -*-
"""SVG generators for the almanac: natal chart, Vimshopaka bars, SAV histogram,
field×player bubble, and the annual Varshaphala diagrams."""
import math

import theme
from jyotish import SIGNS_SHORT, PL_RU

PL_ABBR = {"Su":"Со","Mo":"Лу","Ma":"Ма","Me":"Ме","Ju":"Ю","Ve":"Ве","Sa":"Са","Ra":"Ра","Ke":"Ке"}

# SVG cannot inherit the document's CSS variables, so every colour here comes
# from theme.py — otherwise a theme change leaves the diagrams on the old palette.
_SERIF, _DISPLAY, _MONO = theme.FONT_SERIF, theme.FONT_DISPLAY, theme.FONT_MONO

def _q(f, p):
    """Квадрант «поле × игрок».

    Бренд-бук: «no red / green success-failure pairs — nothing here is good or
    bad news». Поэтому четыре состояния различаются интенсивностью одного тона,
    от Meridian до нейтрального, а не сменой цвета с зелёного на красный.
    """
    fs = f >= 28; ps = p >= 12.6
    if fs and ps:     return theme.Q_BOTH,    "реализованная"
    if not fs and ps: return theme.Q_PLAYER,  "держит игрок"
    if fs and not ps: return theme.Q_FIELD,   "держит поле"
    return theme.Q_NEITHER, "зона роста"

def natal_svg(chart):
    S=96; W=H=S*4
    # South-Indian fixed cells: sign index -> (col,row)
    cells={11:(0,0),0:(1,0),1:(2,0),2:(3,0),3:(3,1),4:(3,2),5:(3,3),
           6:(3,3) if False else (2,3),7:(1,3),8:(0,3),9:(0,2),10:(0,1)}
    cells={11:(0,0),0:(1,0),1:(2,0),2:(3,0),3:(3,1),4:(3,2),5:(3,3),
           6:(2,3),7:(1,3),8:(0,3),9:(0,2),10:(0,1)}
    occ={s:[] for s in range(12)}
    for k,pl in chart["planets"].items():
        tag=PL_ABBR[k]+("℞" if pl["retro"] else "")
        occ[pl["sign"]].append(tag)
    asc_sign=chart["ascendant"]["sign"]
    p=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart natal">']
    p.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" fill="{theme.PANEL}" stroke="{theme.ACCENT}" stroke-width="1.5"/>')
    for i in range(1,4):
        p.append(f'<line x1="{i*S}" y1="0" x2="{i*S}" y2="{H}" stroke="{theme.LINE}"/>')
        p.append(f'<line x1="0" y1="{i*S}" x2="{W}" y2="{i*S}" stroke="{theme.LINE}"/>')
    p.append(f'<rect x="{S}" y="{S}" width="{2*S}" height="{2*S}" fill="{theme.PANEL}" stroke="none"/>')
    a=chart["ascendant"]
    p.append(f'<text x="{W/2}" y="{H/2-8}" fill="{theme.ACCENT}" font-size="15" text-anchor="middle" font-family="{_DISPLAY}" letter-spacing="2">D-1 · РАШИ</text>')
    p.append(f'<text x="{W/2}" y="{H/2+14}" fill="{theme.MUTED}" font-size="11" text-anchor="middle" font-family="{_SERIF}">{a["sign_ru"]} {a["dms"]}</text>')
    for sgn,(cx,cy) in cells.items():
        x=cx*S; y=cy*S
        p.append(f'<text x="{x+6}" y="{y+16}" fill="{theme.FAINT}" font-size="10" font-family="{_MONO}">{SIGNS_SHORT[sgn]}</text>')
        items=list(occ[sgn])
        if sgn==asc_sign: items=["Асц"]+items
        for j,t in enumerate(items):
            col=theme.ACCENT if t=="Асц" else theme.INK
            fw="700" if t=="Асц" else "500"
            p.append(f'<text x="{x+S/2}" y="{y+34+j*17}" fill="{col}" font-size="13" text-anchor="middle" font-weight="{fw}" font-family="{_SERIF}">{t}</text>')
    p.append('</svg>')
    return "\n".join(p)

def vimshopaka_svg(chart):
    vb=chart["vb"]
    order=sorted(((PL_RU[k],v) for k,v in vb.items()), key=lambda x:-x[1])
    W,H=560,300; x0=112; barmax=W-x0-40; top=18; bh=26; gap=12
    p=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for thr,lbl,col in [(15,"15",theme.Q_BOTH),(12.5,"12.5",theme.Q_PLAYER),(10,"10",theme.Q_NEITHER)]:
        gx=x0+barmax*thr/20
        p.append(f'<line x1="{gx:.1f}" y1="{top-6}" x2="{gx:.1f}" y2="{top+7*(bh+gap)-gap+6}" stroke="{col}" stroke-dasharray="3 4" stroke-width="1" opacity="0.55"/>')
        p.append(f'<text x="{gx:.1f}" y="{top+7*(bh+gap)-gap+20}" fill="{col}" font-size="10" text-anchor="middle" font-family="{_MONO}">{lbl}</text>')
    for i,(name,val) in enumerate(order):
        y=top+i*(bh+gap); w=barmax*val/20
        c=theme.Q_BOTH if val>=15 else theme.Q_PLAYER if val>=12.5 else theme.Q_FIELD if val>=10 else theme.Q_NEITHER
        p.append(f'<text x="{x0-10}" y="{y+bh*0.68:.0f}" fill="{theme.INK}" font-size="13" text-anchor="end" font-family="{_SERIF}">{name}</text>')
        p.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{bh}" rx="3" fill="{c}"/>')
        p.append(f'<text x="{x0+w+8:.1f}" y="{y+bh*0.68:.0f}" fill="{theme.ACCENT2}" font-size="12" font-family="{_MONO}">{val:.2f}</text>')
    p.append('</svg>'); return "\n".join(p)

def sav_svg(chart):
    SAV=chart["sav_house"]; avg=chart["sav_avg"]
    W,H=620,300; x0=44; y0=250; bw=40; gap=8; scale=(y0-40)/44
    p=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    yavg=y0-avg*scale
    p.append(f'<line x1="{x0-6}" y1="{yavg:.1f}" x2="{x0+12*(bw+gap):.1f}" y2="{yavg:.1f}" stroke="{theme.ACCENT}" stroke-dasharray="4 4" stroke-width="1.2"/>')
    p.append(f'<text x="{x0+12*(bw+gap)+2:.0f}" y="{yavg+4:.0f}" fill="{theme.ACCENT}" font-size="10" font-family="{_MONO}">{avg:.0f}</text>')
    for h in range(1,13):
        v=SAV[h]; x=x0+(h-1)*(bw+gap); bh=v*scale; y=y0-bh
        c=theme.Q_BOTH if v>=30 else theme.Q_PLAYER if v>=25 else theme.Q_NEITHER
        p.append(f'<rect x="{x}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" rx="2" fill="{c}"/>')
        p.append(f'<text x="{x+bw/2:.0f}" y="{y-5:.0f}" fill="{theme.INK}" font-size="11" text-anchor="middle" font-family="{_MONO}">{v}</text>')
        p.append(f'<text x="{x+bw/2:.0f}" y="{y0+16:.0f}" fill="{theme.MUTED}" font-size="11" text-anchor="middle" font-family="{_MONO}">{h}</text>')
    p.append('</svg>'); return "\n".join(p)

def bubble_svg(chart):
    SAV=chart["sav_house"]; vb=chart["vb"]; lagna=chart["lagna"]
    from jyotish import RULER
    # player per house = max(lord VB, strongest occupant VB)
    occ_by_house={h:[] for h in range(1,13)}
    for k,pl in chart["planets"].items():
        if k in ("Ra","Ke"): continue
        occ_by_house[pl["house"]].append(vb[k])
    player={}
    for h in range(1,13):
        lord=RULER[(lagna+h-1)%12]
        cand=[vb[lord]]+occ_by_house[h]
        player[h]=max(cand)
    W,H=640,460; ml=64; mb=54; mt=20; mr=20
    xmin,xmax=18,42; ymin,ymax=9,17
    X=lambda v: ml+(v-xmin)/(xmax-xmin)*(W-ml-mr)
    Y=lambda v: (H-mb)-(v-ymin)/(ymax-ymin)*(H-mb-mt)
    p=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    xc=X(28); yc=Y(12.6)
    p.append(f'<rect x="{ml}" y="{mt}" width="{W-ml-mr}" height="{H-mb-mt}" fill="{theme.PANEL}" stroke="{theme.LINE}"/>')
    p.append(f'<line x1="{xc:.0f}" y1="{mt}" x2="{xc:.0f}" y2="{H-mb}" stroke="{theme.LINE}" stroke-dasharray="4 4"/>')
    p.append(f'<line x1="{ml}" y1="{yc:.0f}" x2="{W-mr}" y2="{yc:.0f}" stroke="{theme.LINE}" stroke-dasharray="4 4"/>')
    p.append(f'<text x="{ml+8}" y="{mt+16}" fill="{theme.Q_PLAYER}" font-size="10" font-family="{_SERIF}">держит игрок</text>')
    p.append(f'<text x="{W-mr-8}" y="{mt+16}" fill="{theme.Q_BOTH}" font-size="10" text-anchor="end" font-family="{_SERIF}">реализованная сила</text>')
    p.append(f'<text x="{ml+8}" y="{H-mb-6}" fill="{theme.Q_NEITHER}" font-size="10" font-family="{_SERIF}">зона роста</text>')
    p.append(f'<text x="{W-mr-8}" y="{H-mb-6}" fill="{theme.Q_FIELD}" font-size="10" text-anchor="end" font-family="{_SERIF}">держит поле</text>')
    p.append(f'<text x="{(ml+W-mr)/2:.0f}" y="{H-14}" fill="{theme.MUTED}" font-size="12" text-anchor="middle" font-family="{_SERIF}">Сила ПОЛЯ (бинду) →</text>')
    p.append(f'<text x="18" y="{(mt+H-mb)/2:.0f}" fill="{theme.MUTED}" font-size="12" text-anchor="middle" font-family="{_SERIF}" transform="rotate(-90 18 {(mt+H-mb)/2:.0f})">Сила ИГРОКА (Вимшопака) →</text>')
    for h in range(1,13):
        f=SAV[h]; pl=player[h]; c,_=_q(f,pl); r=13
        cx=X(min(max(f,xmin),xmax)); cy=Y(min(max(pl,ymin),ymax))
        p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{c}" opacity="0.85" stroke="{theme.PANEL}" stroke-width="1.2"/>')
        p.append(f'<text x="{cx:.1f}" y="{cy+4:.1f}" fill="#ffffff" font-size="12" font-weight="600" text-anchor="middle" font-family="{_MONO}">{h}</text>')
    p.append('</svg>')
    return "\n".join(p), player

# ============================================================================
# Годовой слой (Варшапхала). Всё — инлайн-SVG: документ остаётся векторным,
# масштабируется без потерь и печатается в PDF без растровых вставок.
# ============================================================================

def _valence_color(v):
    """Цвет по знаку исхода.

    Бренд-бук запрещает пару «зелёное-красное»: ничто здесь не «хорошая» или
    «плохая» новость. Знак несёт направление (выше или ниже нуля), а цвет —
    только интенсивность одного тона.
    """
    if v >= 1.5:  return theme.Q_BOTH
    if v >= 0:    return theme.Q_PLAYER
    if v >= -1.5: return theme.Q_FIELD
    return theme.Q_NEITHER


def muntha_wheel_svg(months, muntha_sign, lagna_sign):
    """16 — кольцо двенадцати знаков с метками месяцев на внешнем радиусе."""
    W = H = 460
    cx = cy = W / 2
    r_out, r_in = 168, 116
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart wheel">']
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{r_out}" fill="{theme.PANEL}" stroke="{theme.LINE}"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{r_in}" fill="{theme.PAPER}" stroke="{theme.LINE_SOFT}"/>')

    for i, m in enumerate(months):
        a0 = math.radians(-90 + i * 30)
        a1 = math.radians(-90 + (i + 1) * 30)
        am = (a0 + a1) / 2
        col = _valence_color(m["valence"])
        x0, y0 = cx + r_in * math.cos(a0), cy + r_in * math.sin(a0)
        x1, y1 = cx + r_out * math.cos(a0), cy + r_out * math.sin(a0)
        x2, y2 = cx + r_out * math.cos(a1), cy + r_out * math.sin(a1)
        x3, y3 = cx + r_in * math.cos(a1), cy + r_in * math.sin(a1)
        p.append(f'<path d="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f} '
                 f'A{r_out} {r_out} 0 0 1 {x2:.1f} {y2:.1f} L{x3:.1f} {y3:.1f} '
                 f'A{r_in} {r_in} 0 0 0 {x0:.1f} {y0:.1f} Z" '
                 f'fill="{col}" opacity="0.85" stroke="{theme.PANEL}" stroke-width="1"/>')
        # знак — внутри кольца, месяц — снаружи
        rx, ry = cx + (r_in + 26) * math.cos(am), cy + (r_in + 26) * math.sin(am)
        p.append(f'<text x="{rx:.1f}" y="{ry:.1f}" fill="#ffffff" font-size="12" '
                 f'font-weight="600" text-anchor="middle" font-family="{_MONO}">'
                 f'{SIGNS_SHORT[m["sign"]]}</text>')
        lx, ly = cx + (r_out + 20) * math.cos(am), cy + (r_out + 20) * math.sin(am)
        p.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" fill="{col}" font-size="11.5" '
                 f'text-anchor="middle" font-family="{_MONO}">{m["label"]}</text>')

    p.append(f'<text x="{cx}" y="{cy - 8}" fill="{theme.ACCENT}" font-size="13" '
             f'text-anchor="middle" font-family="{_DISPLAY}" letter-spacing="2">МУНТХА</text>')
    p.append(f'<text x="{cx}" y="{cy + 14}" fill="{theme.INK}" font-size="15" '
             f'text-anchor="middle" font-family="{_SERIF}">{SIGNS_SHORT[muntha_sign]}</text>')
    p.append(f'<text x="{cx}" y="{cy + 34}" fill="{theme.MUTED}" font-size="11" '
             f'text-anchor="middle" font-family="{_SERIF}">'
             f'{(muntha_sign - lagna_sign) % 12 + 1}-й дом</text>')
    p.append('</svg>')
    return "\n".join(p)


def monthly_axes_svg(months):
    """17 — две независимые оси по месяцам.

    Салиентность (громкость денежной темы) — столбцы вверх от базовой линии,
    она всегда ≥ 0. Знак исхода — отдельная ломаная вокруг нуля, уходящая ниже
    него. Это НЕ одна шкала: месяц с громкой темой и отрицательным знаком —
    когда деньги звучат много и плохо — обязан читаться иначе, чем тихий месяц.
    """
    W, H = 720, 340
    ml, mr, mt, mb = 54, 24, 26, 58
    plot_w = W - ml - mr
    zero_y = H - mb - 84                    # ноль второй оси
    bar_base = H - mb                       # база столбцов салиентности
    step = plot_w / 12
    bw = step * 0.52

    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    p.append(f'<rect x="{ml}" y="{mt}" width="{plot_w}" height="{H - mt - mb}" '
             f'fill="{theme.PANEL}" stroke="{theme.LINE}"/>')

    # столбцы: громкость темы
    for i, m in enumerate(months):
        x = ml + i * step + (step - bw) / 2
        h = (m["salience"] / 10.0) * (bar_base - mt - 12)
        p.append(f'<rect x="{x:.1f}" y="{bar_base - h:.1f}" width="{bw:.1f}" '
                 f'height="{h:.1f}" rx="2" fill="{theme.ACCENT_SOFT}" '
                 f'stroke="{theme.SHOAL}" stroke-width="0.8"/>')
        p.append(f'<text x="{ml + i * step + step / 2:.1f}" y="{bar_base + 16:.0f}" '
                 f'fill="{theme.MUTED}" font-size="10" text-anchor="middle" '
                 f'font-family="{_MONO}">{m["label"]}</text>')

    # ломаная: знак исхода, с уходом ниже нуля
    p.append(f'<line x1="{ml}" y1="{zero_y}" x2="{W - mr}" y2="{zero_y}" '
             f'stroke="{theme.LINE}" stroke-dasharray="4 4"/>')
    p.append(f'<text x="{ml - 8}" y="{zero_y + 4}" fill="{theme.FAINT}" font-size="10" '
             f'text-anchor="end" font-family="{_MONO}">0</text>')
    pts = []
    for i, m in enumerate(months):
        x = ml + i * step + step / 2
        y = zero_y - (m["valence"] / 5.0) * 62
        pts.append((x, y, m["valence"]))
    p.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts) +
             f'" fill="none" stroke="{theme.ACCENT2}" stroke-width="2"/>')
    for x, y, v in pts:
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{_valence_color(v)}" '
                 f'stroke="{theme.PANEL}" stroke-width="1.2"/>')

    p.append(f'<text x="{ml}" y="{mt - 10}" fill="{theme.SHOAL}" font-size="11" '
             f'font-family="{_SERIF}">▮ громкость денежной темы (0–10)</text>')
    p.append(f'<text x="{W - mr}" y="{mt - 10}" fill="{theme.ACCENT2}" font-size="11" '
             f'text-anchor="end" font-family="{_SERIF}">— знак исхода (−5…+5)</text>')
    p.append(f'<text x="{(ml + W - mr) / 2:.0f}" y="{H - 10}" fill="{theme.FAINT}" '
             f'font-size="10.5" text-anchor="middle" font-family="{_SERIF}">'
             f'громко и в минусе — не то же самое, что тихо: это разные оси</text>')
    p.append('</svg>')
    return "\n".join(p)


def dasha_gantt_svg(dashas, start, end):
    """18 — пять дорожек на общей оси времени."""
    names = list(dashas.keys())
    W = 720
    track_h, gap = 30, 12
    ml, mr, mt = 132, 16, 24
    H = mt + len(names) * (track_h + gap) + 34
    span = max((end - start).total_seconds(), 1)
    plot_w = W - ml - mr

    def X(dt):
        return ml + plot_w * (dt - start).total_seconds() / span

    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for r, name in enumerate(names):
        y = mt + r * (track_h + gap)
        p.append(f'<text x="{ml - 10}" y="{y + track_h * 0.68:.0f}" fill="{theme.INK}" '
                 f'font-size="11.5" text-anchor="end" font-family="{_SERIF}">{name}</text>')
        for i, seg in enumerate(dashas[name]):
            x0, x1 = X(seg["start"]), X(seg["end"])
            w = max(x1 - x0, 1.0)
            shade = [theme.Q_BOTH, theme.Q_PLAYER, theme.Q_FIELD, theme.Q_NEITHER][i % 4]
            p.append(f'<rect x="{x0:.1f}" y="{y}" width="{w:.1f}" height="{track_h}" '
                     f'rx="2" fill="{shade}" opacity="0.9" stroke="{theme.PANEL}" '
                     f'stroke-width="1"/>')
            label = str(seg["lord"])
            if w > 7 * len(label):
                p.append(f'<text x="{x0 + w / 2:.1f}" y="{y + track_h * 0.68:.0f}" '
                         f'fill="#ffffff" font-size="10.5" text-anchor="middle" '
                         f'font-family="{_MONO}">{label}</text>')
    y_axis = mt + len(names) * (track_h + gap)
    p.append(f'<line x1="{ml}" y1="{y_axis}" x2="{W - mr}" y2="{y_axis}" stroke="{theme.LINE}"/>')
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        x = ml + plot_w * frac
        d = start + (end - start) * frac
        p.append(f'<line x1="{x:.1f}" y1="{y_axis}" x2="{x:.1f}" y2="{y_axis + 5}" '
                 f'stroke="{theme.LINE}"/>')
        p.append(f'<text x="{x:.1f}" y="{y_axis + 18}" fill="{theme.MUTED}" font-size="10" '
                 f'text-anchor="middle" font-family="{_MONO}">{d:%d.%m.%y}</text>')
    p.append('</svg>')
    return "\n".join(p)


def stacked_bala_svg(rows, maximum, title):
    """19 — стековые столбцы с разбивкой по составляющим.

    rows: [(подпись, {составляющая: значение})]. Показывает не только сумму, но
    и чем именно набрана сила: два одинаковых итога с разной разбивкой — разные
    ситуации.
    """
    if not rows:
        return ""
    comps, seen = [], set()
    for _, parts in rows:
        for k in parts:
            if k not in seen:
                seen.add(k)
                comps.append(k)
    palette = [theme.Q_BOTH, theme.Q_PLAYER, theme.Q_FIELD, theme.Q_NEITHER, theme.SHOAL]
    col = {c: palette[i % len(palette)] for i, c in enumerate(comps)}

    W = 640
    ml, mr, mt = 118, 46, 22
    bh, gap = 24, 11
    legend_h = 20 * ((len(comps) + 2) // 3)
    H = mt + len(rows) * (bh + gap) + legend_h + 16
    barmax = W - ml - mr

    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for i, (label, parts) in enumerate(rows):
        y = mt + i * (bh + gap)
        p.append(f'<text x="{ml - 10}" y="{y + bh * 0.7:.0f}" fill="{theme.INK}" '
                 f'font-size="12" text-anchor="end" font-family="{_SERIF}">{label}</text>')
        x = ml
        for c in comps:
            v = parts.get(c, 0) or 0
            w = barmax * v / maximum
            if w > 0.5:
                p.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bh}" '
                         f'fill="{col[c]}" stroke="{theme.PANEL}" stroke-width="0.8"/>')
            x += w
        p.append(f'<text x="{x + 7:.1f}" y="{y + bh * 0.7:.0f}" fill="{theme.ACCENT2}" '
                 f'font-size="11.5" font-family="{_MONO}">{sum(parts.values()):.1f}</text>')
    ly = mt + len(rows) * (bh + gap) + 6
    for i, c in enumerate(comps):
        cx = ml + (i % 3) * ((W - ml - mr) / 3)
        cyy = ly + (i // 3) * 20
        p.append(f'<rect x="{cx:.0f}" y="{cyy:.0f}" width="10" height="10" fill="{col[c]}"/>')
        p.append(f'<text x="{cx + 15:.0f}" y="{cyy + 9:.0f}" fill="{theme.MUTED}" '
                 f'font-size="10.5" font-family="{_SERIF}">{c}</text>')
    p.append('</svg>')
    return "\n".join(p)


def saham_grid_svg(months):
    """22 — матрица «месяцы × сахамы», цвет ячейки = статус темы."""
    rows = max((len(m["saham_records"]) for m in months), default=0)
    if not rows:
        return ""
    W = 760
    ml, mt, mr = 8, 46, 8
    cw = (W - ml - mr) / 12
    ch = 22
    H = mt + rows * (ch + 3) + 12

    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for i, m in enumerate(months):
        x = ml + i * cw
        p.append(f'<text x="{x + cw / 2:.1f}" y="{mt - 24}" fill="{theme.INK}" '
                 f'font-size="10.5" text-anchor="middle" font-family="{_MONO}">{m["label"]}</text>')
        p.append(f'<text x="{x + cw / 2:.1f}" y="{mt - 10}" fill="{theme.FAINT}" '
                 f'font-size="9.5" text-anchor="middle" font-family="{_MONO}">'
                 f'{SIGNS_SHORT[m["sign"]]}</text>')
        for j, s in enumerate(m["saham_records"]):
            y = mt + j * (ch + 3)
            risky = any(w in s["meaning"] for w in ("риск", "беречь", "осторожность"))
            col = theme.Q_FIELD if risky else theme.Q_BOTH
            if not s.get("verified", True):
                col = theme.Q_NEITHER
            p.append(f'<rect x="{x + 1:.1f}" y="{y}" width="{cw - 2:.1f}" height="{ch}" '
                     f'rx="2" fill="{col}" opacity="0.9"/>')
            name = s["name"] if len(s["name"]) <= 9 else s["name"][:8] + "…"
            p.append(f'<text x="{x + cw / 2:.1f}" y="{y + ch * 0.7:.0f}" fill="#ffffff" '
                     f'font-size="9.5" text-anchor="middle" font-family="{_SERIF}">{name}</text>')
    p.append('</svg>')
    return "\n".join(p)


def year_compare_svg(series, labels, title, maximum=None):
    """21 — столбцы по годам для одного параметра."""
    if not series:
        return ""
    top = maximum or max(max(v for v in s) for s in series.values()) or 1
    W = 640
    ml, mr, mt, mb = 132, 30, 20, 34
    plot_w = W - ml - mr
    rowh = 30
    H = mt + len(series) * rowh + mb
    n = len(labels)
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for i, (param, vals) in enumerate(series.items()):
        y = mt + i * rowh
        p.append(f'<text x="{ml - 10}" y="{y + 15}" fill="{theme.INK}" font-size="11.5" '
                 f'text-anchor="end" font-family="{_SERIF}">{param}</text>')
        gw = plot_w / n
        for k, v in enumerate(vals):
            bw = gw * 0.7
            x = ml + k * gw + (gw - bw) / 2
            hgt = 18
            frac = min(max(v / top, 0), 1)
            p.append(f'<rect x="{x:.1f}" y="{y + 2}" width="{bw * frac:.1f}" height="{hgt}" '
                     f'rx="2" fill="{[theme.Q_BOTH, theme.Q_PLAYER, theme.Q_FIELD][k % 3]}"/>')
            p.append(f'<rect x="{x:.1f}" y="{y + 2}" width="{bw:.1f}" height="{hgt}" '
                     f'fill="none" stroke="{theme.LINE_SOFT}"/>')
            p.append(f'<text x="{x + bw / 2:.1f}" y="{y + 15}" fill="{theme.INK}" '
                     f'font-size="10" text-anchor="middle" font-family="{_MONO}">{v:g}</text>')
    for k, lb in enumerate(labels):
        gw = plot_w / n
        p.append(f'<text x="{ml + k * gw + gw / 2:.1f}" y="{H - 12}" fill="{theme.MUTED}" '
                 f'font-size="10.5" text-anchor="middle" font-family="{_MONO}">{lb}</text>')
    p.append('</svg>')
    return "\n".join(p)


def months_overlay_svg(years):
    """21 — помесячный балл всех лет наложением на одной шкале.

    years: [(подпись, [12 значений валентности])]. Тренд между годами виден
    только здесь: в отдельной части каждый год выглядит самодостаточным.
    """
    if not years:
        return ""
    W, H = 720, 260
    ml, mr, mt, mb = 46, 90, 22, 40
    plot_w, plot_h = W - ml - mr, H - mt - mb
    zero = mt + plot_h / 2
    step = plot_w / 11
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    p.append(f'<rect x="{ml}" y="{mt}" width="{plot_w}" height="{plot_h}" '
             f'fill="{theme.PANEL}" stroke="{theme.LINE}"/>')
    p.append(f'<line x1="{ml}" y1="{zero}" x2="{W - mr}" y2="{zero}" '
             f'stroke="{theme.LINE}" stroke-dasharray="4 4"/>')
    shades = [theme.MERIDIAN, theme.SHOAL, theme.Q_NEITHER, theme.MERIDIAN_DARK]
    for k, (label, vals) in enumerate(years):
        col = shades[k % len(shades)]
        pts = " ".join(f"{ml + i * step:.1f},{zero - (v / 5.0) * (plot_h / 2 - 8):.1f}"
                       for i, v in enumerate(vals))
        p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" '
                 f'opacity="0.9"/>')
        p.append(f'<text x="{W - mr + 8}" y="{mt + 14 + k * 17}" fill="{col}" '
                 f'font-size="11" font-family="{_MONO}">{label}</text>')
    for i in range(12):
        p.append(f'<text x="{ml + i * step:.1f}" y="{H - 16}" fill="{theme.MUTED}" '
                 f'font-size="10" text-anchor="middle" font-family="{_MONO}">{i + 1}</text>')
    p.append(f'<text x="{(ml + W - mr) / 2:.0f}" y="{H - 3}" fill="{theme.FAINT}" '
             f'font-size="10" text-anchor="middle" font-family="{_SERIF}">'
             f'месяц года (1 — от входа в год)</text>')
    p.append('</svg>')
    return "\n".join(p)


# Сетка достоинств «планета × 16 варг» удалена вместе с разделом, который её
# показывал. Итоговый Вимшопака-балл и его столбчатый график остались — они
# переехали в «Интегральную карту», где балл и есть ось «игрок».
