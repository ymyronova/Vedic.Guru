# -*- coding: utf-8 -*-
"""
Токены бренда Vedic Guru — единственный источник палитры и шрифтов.

Источник: «Vedic Guru Brand Book», страницы 03 Color (P2 · locked) и
04 Typography (T1 · locked). Значения не изобретены и не подобраны на глаз —
менять их можно только вслед за бренд-буком.

Зачем отдельный модуль: цвета встречаются и в CSS (render.py), и внутри
генерируемых SVG (charts.py). SVG не наследует CSS-переменные документа,
поэтому без общего источника смена темы оставила бы диаграммы старого цвета.

──────────────────────────────────────────────────────────────────────────────
Правила бренд-бука, которые здесь закодированы
──────────────────────────────────────────────────────────────────────────────
1. «No red / green success-failure pairs: nothing here is good or bad news.»
   Прямо запрещает прежнюю схему «зелёный — сильный дом, красный — уязвимый».
   Сила теперь передаётся ИНТЕНСИВНОСТЬЮ одного тона (Meridian → нейтральный
   серо-зелёный), а не сменой цвета: шкала, а не оценка.

2. «Meridian never appears on a background darker than Leaf — Shoal takes over.»
   Поэтому MERIDIAN только на PAPER/LEAF; для тёмных подложек есть SHOAL.

3. «MERIDIAN … ≤10%» — акцент только на вычисленных значениях и главном
   действии. Не на заголовках, не на рамках, не на фоне.

4. Соотношение поверхностей 70 / 14 / 9 / 7 — Paper доминирует.

Контраст (из бренд-бука): Ink на Paper 15.8:1 AAA · Meridian на Paper 4.6:1 AA
· Shoal на Ink 7.4:1 AAA.
"""

# ─── Поверхности ──────────────────────────────────────────────────────────────
PAPER   = "#F7F8F6"          # «All surfaces, reports, web. ~70% of any layout.»
PANEL   = "#FFFFFF"          # карточки поверх Paper
PANEL2  = "#E7EAE7"          # LEAF: вторые панели, цитаты, зебра таблиц
LEAF    = PANEL2

# ─── Акцент ───────────────────────────────────────────────────────────────────
MERIDIAN = "#1E7A7F"         # вычисленные значения, главное действие, точка бренда
MERIDIAN_DARK = "#135A5E"    # ховер/нажатие
SHOAL   = "#6FAFAF"          # Meridian на тёмном — только там
ACCENT  = MERIDIAN
ACCENT2 = MERIDIAN_DARK
ACCENT_WASH = "rgba(30,122,127,.07)"   # едва заметная заливка акцентом
ACCENT_SOFT = "rgba(30,122,127,.14)"   # подсветка текущей строки

# ─── Текст ────────────────────────────────────────────────────────────────────
INK     = "#16201F"          # «Type, rules, the decided cell.»
BODY    = "#454F4D"          # «Body at #454F4D.»
MUTED   = "#454F4D"
FAINT   = "#7C8683"          # подписи, третичное

# ─── Линии ────────────────────────────────────────────────────────────────────
LINE      = "#D3DAD7"
LINE_SOFT = "#E7EAE7"

# ─── Шкала силы вместо «хорошо/плохо» ─────────────────────────────────────────
# Прежние GREEN/BLUE/YELLOW/RED кодировали оценку. Бренд-бук это запрещает,
# поэтому здесь один тон в четырёх интенсивностях: от Meridian (обе силы
# высокие) до нейтрального серо-зелёного (обе низкие). Различие читается, но
# ни один дом не «плохой» — это шкала, а не приговор.
Q_BOTH    = MERIDIAN         # поле и игрок сильны
Q_PLAYER  = "#4E9497"        # держит игрок
Q_FIELD   = "#93B7B6"        # держит поле
Q_NEITHER = "#96A09D"        # оба слабы — нейтральный, НЕ красный

# Совместимость со старыми именами (charts.py/render.py переведены на Q_*).
GREEN, BLUE, YELLOW, RED = Q_BOTH, Q_PLAYER, Q_FIELD, Q_NEITHER
SATURN = "#7C8683"

# Достоинства планет — та же логика: сила через интенсивность одного тона.
DIGNITY_COLORS = {
    "Э":  MERIDIAN, "МТ": MERIDIAN, "С": "#3E8A8D",
    "дд": "#4E9497", "д": "#6BA5A6", "н": FAINT,
    "в":  "#9AA5A2", "вв": "#A9B3B0", "П": "#B9C2BF",
}

# ─── Шрифты ───────────────────────────────────────────────────────────────────
# Newsreader — «Headlines, manifesto, pull quotes, report titles.»
# Helvetica Neue — «Body copy, navigation, buttons, forms.»
# IBM Plex Mono — «Every computed value, timestamp, checksum, eyebrow label.»
#
# Локальные запасные варианты обязательны: PDF собирается WeasyPrint внутри
# контейнера, где веб-шрифты недоступны, а без запасного шрифта кириллица
# выйдет квадратами.
FONT_DISPLAY = "'Newsreader','DejaVu Serif',Georgia,'Times New Roman',serif"
FONT_SANS    = "'Helvetica Neue',Helvetica,Arial,'DejaVu Sans',sans-serif"
FONT_SERIF   = FONT_SANS          # интерфейсный и основной текст — по бренду сансериф
FONT_MONO    = "'IBM Plex Mono','DejaVu Sans Mono',ui-monospace,'Courier New',monospace"

GOOGLE_FONTS = ("https://fonts.googleapis.com/css2"
                "?family=Newsreader:ital,opsz,wght@0,6..72,200;0,6..72,300;"
                "0,6..72,400;0,6..72,500;1,6..72,300;1,6..72,400"
                "&family=IBM+Plex+Mono:wght@400;500&display=swap")

# ─── Типографическая шкала (04 Typography · ratio 1.28) ───────────────────────
# (размер px, межстрочный, трекинг)
TYPE = {
    "manifesto": (56,   1.05, "-2.5%"),
    "section":   (34,   1.15, "-1.5%"),
    "subhead":   (22,   1.30, "0"),
    "body":      (17,   1.65, "0"),
    "caption":   (13.5, 1.55, "0"),
    "eyebrow":   (10.5, 1.40, "16%"),
}
