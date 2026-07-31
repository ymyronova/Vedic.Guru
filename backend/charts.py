# -*- coding: utf-8 -*-
"""SVG generators for the almanac: natal chart, Vimshopaka bars, SAV histogram, field×player bubble."""
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

def dignity_grid_html(chart):
    from jyotish import VARGAS
    vargas=list(VARGAS.keys())
    dcolor=theme.DIGNITY_COLORS
    rows=["<table class='grid'><thead><tr><th>Планета</th>"+"".join(f"<th>{v}</th>" for v in vargas)+"</tr></thead><tbody>"]
    for k in ["Su","Mo","Ma","Me","Ju","Ve","Sa"]:
        cells=f"<td class='pl'>{PL_RU[k]}</td>"
        for v in vargas:
            dg=chart["grid"][k][v]["dignity"]
            cells+=f"<td style='color:{dcolor[dg]}'>{dg}</td>"
        rows.append("<tr>"+cells+"</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)
