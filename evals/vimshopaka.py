#!/usr/bin/env python3
"""
vimshopaka.py — расчёт Вимшопака-балла по Шодашаварге (16 дробных карт).

Почему этот модуль существует
------------------------------
История та же, что и с Аштакаваргой. В выпущенных альманахах Вимшопака-баллы
проставлялись оценочно: «Венера сильная — пусть будет 15.1». Числа выглядели
правдоподобно, но не были посчитаны, и проверить их было нечем.

Вимшопака — детерминированная величина с жёстким инвариантом:
веса шестнадцати варг в сумме дают ровно 20, поэтому балл всегда лежит
в диапазоне [3.0, 20.0]. Если сумма весов не 20 — таблица повреждена.

Что считается
-------------
Для каждой из 7 грах определяется знак в каждой из 16 варг, по знаку —
достоинство (экзальтация / мулатрикона / свой / друг / нейтрал / враг /
падение), достоинство переводится в коэффициент, коэффициент умножается
на вес варги. Сумма по всем варгам и есть Вимшопака-балл.

    ВБ = Σ (вес_варги × достоинство/20)

Выбор шкалы достоинств
----------------------
В источниках встречаются разные шкалы. Здесь использована наиболее
распространённая парашаровская; значения вынесены в DIGNITY_VALUES,
чтобы выбор был явным и заменяемым, а не спрятанным в коде.
"""

from typing import Dict, List, Tuple

# ─── Константы ────────────────────────────────────────────────────────────────

PLANETS = ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa']

RU = {'Su': 'Солнце', 'Mo': 'Луна', 'Ma': 'Марс', 'Me': 'Меркурий',
      'Ju': 'Юпитер', 'Ve': 'Венера', 'Sa': 'Сатурн'}

SIGNS = ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева',
         'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы']

# Веса 16 варг. ИНВАРИАНТ: сумма ровно 20.
VARGA_WEIGHTS: Dict[str, float] = {
    'D1':  3.5,   # Раши — физическое тело, основа
    'D2':  1.0,   # Хора — благосостояние
    'D3':  1.0,   # Дреккана — братья, инициатива
    'D4':  0.5,   # Чатуртхамша — дом, имущество
    'D7':  0.5,   # Саптамамша — дети, потомство
    'D9':  3.0,   # Навамша — супруг, дхарма, общая сила
    'D10': 0.5,   # Дашамамша — карьера, действия
    'D12': 0.5,   # Двадашамша — родители
    'D16': 2.0,   # Шодашамша — комфорт, транспорт
    'D20': 0.5,   # Вимшамша — духовная практика
    'D24': 0.5,   # Чатурвимшамша — образование, знание
    'D27': 0.5,   # Бхамша — сила, выносливость
    'D30': 1.0,   # Тримшамша — беды, слабости
    'D40': 0.5,   # Кхаведамша — благо по материнской линии
    'D45': 0.5,   # Акшаведамша — благо по отцовской линии
    'D60': 4.0,   # Шаштиамша — тонкая карма, итог
}
WEIGHTS_CHECKSUM = 20.0

# Шкала достоинств (0–20). Делится на 20 → коэффициент 0.15…1.0
DIGNITY_VALUES: Dict[str, int] = {
    'Э':  20,   # экзальтация
    'МТ': 18,   # мулатрикона
    'С':  17,   # собственный знак
    'дд': 15,   # великий друг
    'д':  12,   # друг
    'н':  10,   # нейтрал
    'в':   7,   # враг
    'вв':  5,   # великий враг
    'П':   3,   # падение
}
DIGNITY_LABELS = {
    'Э': 'экзальтация', 'МТ': 'мулатрикона', 'С': 'свой знак',
    'дд': 'великий друг', 'д': 'друг', 'н': 'нейтрал',
    'в': 'враг', 'вв': 'великий враг', 'П': 'падение',
}

VB_MIN = round(WEIGHTS_CHECKSUM * DIGNITY_VALUES['П'] / 20, 2)   # 3.0
VB_MAX = round(WEIGHTS_CHECKSUM * DIGNITY_VALUES['Э'] / 20, 2)   # 20.0

# Пороги интерпретации (используются в текстах альманахов)
VB_EXCELLENT = 15.0
VB_GOOD = 12.5
VB_NORMAL = 10.0

# Управители знаков (индекс знака 0–11 → планета)
SIGN_LORDS = ['Ma', 'Ve', 'Me', 'Mo', 'Su', 'Me',
              'Ve', 'Ma', 'Ju', 'Sa', 'Sa', 'Ju']

# Экзальтация: планета → индекс знака
EXALTATION = {'Su': 0, 'Mo': 1, 'Ma': 9, 'Me': 5, 'Ju': 3, 'Ve': 11, 'Sa': 6}
# Падение — всегда 7-й знак от экзальтации
DEBILITATION = {p: (s + 6) % 12 for p, s in EXALTATION.items()}

# Мулатрикона: планета → (знак, градус_от, градус_до). Применяется только в D1.
MOOLATRIKONA = {
    'Su': (4, 0, 20), 'Mo': (1, 4, 30), 'Ma': (0, 0, 12), 'Me': (5, 16, 20),
    'Ju': (8, 0, 10), 'Ve': (6, 0, 15), 'Sa': (10, 0, 20),
}

# Натуральная дружба (Парашара)
NATURAL_FRIENDS = {
    'Su': {'Mo', 'Ma', 'Ju'},
    'Mo': {'Su', 'Me'},
    'Ma': {'Su', 'Mo', 'Ju'},
    'Me': {'Su', 'Ve'},
    'Ju': {'Su', 'Mo', 'Ma'},
    'Ve': {'Me', 'Sa'},
    'Sa': {'Me', 'Ve'},
}
NATURAL_ENEMIES = {
    'Su': {'Ve', 'Sa'},
    'Mo': set(),
    'Ma': {'Me'},
    'Me': {'Mo'},
    'Ju': {'Me', 'Ve'},
    'Ve': {'Su', 'Mo'},
    'Sa': {'Su', 'Mo', 'Ma'},
}

MOVABLE = {0, 3, 6, 9}      # Овен, Рак, Весы, Козерог
FIXED = {1, 4, 7, 10}       # Телец, Лев, Скорпион, Водолей
DUAL = {2, 5, 8, 11}        # Близнецы, Дева, Стрелец, Рыбы


class VimshopakaError(Exception):
    """Инвариант нарушен — результату доверять нельзя."""
    pass


# ─── Расчёт варг ──────────────────────────────────────────────────────────────
# Каждая функция: (индекс знака 0–11, градус в знаке 0–30) → индекс знака в варге

def _d1(s, d):
    return s

def _d2(s, d):
    """Хора. Нечётные знаки: 1-я половина Лев, 2-я Рак. Чётные — наоборот."""
    first = d < 15
    odd = s % 2 == 0
    return 4 if (odd == first) else 3

def _d3(s, d):
    """Дреккана. Трети по 10°: сам знак, 5-й, 9-й."""
    return (s + 4 * int(d / 10)) % 12

def _d4(s, d):
    """Чатуртхамша. Четверти по 7°30': сам, 4-й, 7-й, 10-й."""
    return (s + 3 * int(d / 7.5)) % 12

def _d7(s, d):
    """Саптамамша. Нечётные — от своего знака, чётные — от 7-го."""
    start = s if s % 2 == 0 else (s + 6) % 12
    return (start + int(d / (30 / 7))) % 12

def _d9(s, d):
    """Навамша. Подвижные от себя, фиксированные от 9-го, двойственные от 5-го."""
    if s in MOVABLE:
        start = s
    elif s in FIXED:
        start = (s + 8) % 12
    else:
        start = (s + 4) % 12
    return (start + int(d / (30 / 9))) % 12

def _d10(s, d):
    """Дашамамша. Нечётные — от себя, чётные — от 9-го."""
    start = s if s % 2 == 0 else (s + 8) % 12
    return (start + int(d / 3)) % 12

def _d12(s, d):
    """Двадашамша. Всегда от своего знака."""
    return (s + int(d / 2.5)) % 12

def _d16(s, d):
    """Шодашамша. Подвижные — Овен, фиксированные — Лев, двойственные — Стрелец."""
    start = 0 if s in MOVABLE else (4 if s in FIXED else 8)
    return (start + int(d / (30 / 16))) % 12

def _d20(s, d):
    """Вимшамша. Подвижные — Овен, фиксированные — Стрелец, двойственные — Лев."""
    start = 0 if s in MOVABLE else (8 if s in FIXED else 4)
    return (start + int(d / 1.5)) % 12

def _d24(s, d):
    """Чатурвимшамша. Нечётные — от Льва, чётные — от Рака."""
    start = 4 if s % 2 == 0 else 3
    return (start + int(d / 1.25)) % 12

def _d27(s, d):
    """Бхамша. Огонь — Овен, земля — Рак, воздух — Весы, вода — Козерог."""
    start = (s % 4) * 3
    return (start + int(d / (30 / 27))) % 12

def _d30(s, d):
    """Тримшамша. Неравные части, знаки только нечётные/чётные по управителям."""
    if s % 2 == 0:  # нечётный знак (Овен=0 → 1-й)
        if d < 5:    return 0    # Марс → Овен
        if d < 10:   return 10   # Сатурн → Водолей
        if d < 18:   return 8    # Юпитер → Стрелец
        if d < 25:   return 2    # Меркурий → Близнецы
        return 6                 # Венера → Весы
    else:           # чётный знак
        if d < 5:    return 1    # Венера → Телец
        if d < 12:   return 5    # Меркурий → Дева
        if d < 20:   return 11   # Юпитер → Рыбы
        if d < 25:   return 9    # Сатурн → Козерог
        return 7                 # Марс → Скорпион

def _d40(s, d):
    """Кхаведамша. Нечётные — от Овна, чётные — от Весов."""
    start = 0 if s % 2 == 0 else 6
    return (start + int(d / 0.75)) % 12

def _d45(s, d):
    """Акшаведамша. Подвижные — Овен, фиксированные — Лев, двойственные — Стрелец."""
    start = 0 if s in MOVABLE else (4 if s in FIXED else 8)
    return (start + int(d / (30 / 45))) % 12

def _d60(s, d):
    """Шаштиамша. Части по 0°30' от своего знака."""
    return (s + int(d * 2)) % 12


VARGA_FUNCTIONS = {
    'D1': _d1, 'D2': _d2, 'D3': _d3, 'D4': _d4, 'D7': _d7, 'D9': _d9,
    'D10': _d10, 'D12': _d12, 'D16': _d16, 'D20': _d20, 'D24': _d24,
    'D27': _d27, 'D30': _d30, 'D40': _d40, 'D45': _d45, 'D60': _d60,
}


# ─── Достоинство ──────────────────────────────────────────────────────────────

def get_dignity(planet: str, sign_index: int,
                degree: float = None, is_d1: bool = False) -> str:
    """
    Определяет достоинство планеты в знаке.
    Мулатрикона проверяется только для D1 (там имеет значение градус).
    """
    if sign_index == EXALTATION[planet]:
        return 'Э'
    if sign_index == DEBILITATION[planet]:
        return 'П'

    if is_d1 and degree is not None and planet in MOOLATRIKONA:
        mt_sign, mt_from, mt_to = MOOLATRIKONA[planet]
        if sign_index == mt_sign and mt_from <= degree < mt_to:
            return 'МТ'

    lord = SIGN_LORDS[sign_index]
    if lord == planet:
        return 'С'
    if lord in NATURAL_FRIENDS[planet]:
        return 'д'
    if lord in NATURAL_ENEMIES[planet]:
        return 'в'
    return 'н'


# ─── Самопроверка ─────────────────────────────────────────────────────────────

def validate_tables() -> Tuple[bool, List[str]]:
    """Проверяет инварианты констант. Вызывается при импорте."""
    errors = []

    total = sum(VARGA_WEIGHTS.values())
    if abs(total - WEIGHTS_CHECKSUM) > 1e-9:
        errors.append(f"Сумма весов варг {total}, ожидается {WEIGHTS_CHECKSUM}")

    if len(VARGA_WEIGHTS) != 16:
        errors.append(f"Варг {len(VARGA_WEIGHTS)}, ожидается 16")

    missing = set(VARGA_WEIGHTS) - set(VARGA_FUNCTIONS)
    if missing:
        errors.append(f"Нет функций для варг: {sorted(missing)}")

    for p in PLANETS:
        if (EXALTATION[p] + 6) % 12 != DEBILITATION[p]:
            errors.append(f"{RU[p]}: падение не в 7-м знаке от экзальтации")

    # Дружба должна быть непротиворечивой: планета не может быть
    # одновременно другом и врагом
    for p in PLANETS:
        both = NATURAL_FRIENDS[p] & NATURAL_ENEMIES[p]
        if both:
            errors.append(f"{RU[p]}: {both} одновременно друг и враг")

    # Все варга-функции должны возвращать корректный индекс
    for name, fn in VARGA_FUNCTIONS.items():
        for s in range(12):
            for d in (0.0, 7.4, 15.0, 22.9, 29.99):
                r = fn(s, d)
                if not isinstance(r, int) or not 0 <= r <= 11:
                    errors.append(f"{name}({s},{d}) вернула {r} — вне 0–11")
                    break

    if len(SIGN_LORDS) != 12:
        errors.append(f"SIGN_LORDS содержит {len(SIGN_LORDS)} записей, нужно 12")

    return len(errors) == 0, errors


_ok, _errs = validate_tables()
if not _ok:
    raise VimshopakaError("Таблицы Вимшопаки повреждены:\n  " + "\n  ".join(_errs))


# ─── Основной расчёт ──────────────────────────────────────────────────────────

def compute_vimshopaka(positions: Dict[str, Tuple[int, float]]) -> dict:
    """
    Считает Вимшопака-балл для каждой из 7 грах.

    Аргументы:
        positions: {'Su': (sign_index, degree_in_sign), ...}
                   sign_index 0–11, degree 0–30.

    Возвращает:
        {
          'scores': {'Солнце': 9.53, ...},
          'grid':   {'Солнце': {'D1': ('Стрелец','д'), ...}, ...},
          'ranking': [('Венера', 15.1, 'превосходно'), ...],
          'validation': {...}
        }
    """
    for p in PLANETS:
        if p not in positions:
            raise ValueError(f"Не передана позиция: {RU[p]} ({p})")
        s, d = positions[p]
        if not 0 <= s <= 11:
            raise ValueError(f"{RU[p]}: индекс знака {s} вне 0–11")
        if not 0 <= d < 30:
            raise ValueError(f"{RU[p]}: градус {d} вне 0–30")

    scores = {}
    grid = {}
    problems = []

    for p in PLANETS:
        s, d = positions[p]
        row = {}
        total = 0.0
        for varga, weight in VARGA_WEIGHTS.items():
            vsign = VARGA_FUNCTIONS[varga](s, d)
            dignity = get_dignity(p, vsign, degree=d, is_d1=(varga == 'D1'))
            row[varga] = (SIGNS[vsign], dignity)
            total += weight * DIGNITY_VALUES[dignity] / 20.0

        total = round(total, 2)
        if not VB_MIN - 0.01 <= total <= VB_MAX + 0.01:
            problems.append(
                f"{RU[p]}: ВБ {total} вне диапазона [{VB_MIN}, {VB_MAX}]")
        scores[RU[p]] = total
        grid[RU[p]] = row

    if problems:
        raise VimshopakaError("Инвариант нарушен:\n  " + "\n  ".join(problems))

    def grade(v):
        if v >= VB_EXCELLENT: return 'превосходно'
        if v >= VB_GOOD:      return 'хорошо'
        if v >= VB_NORMAL:    return 'норма'
        return 'зона роста'

    ranking = sorted(
        [(RU[p], scores[RU[p]], grade(scores[RU[p]])) for p in PLANETS],
        key=lambda x: -x[1])

    return {
        'scores': scores,
        'grid': grid,
        'ranking': ranking,
        'strongest': {'planet': ranking[0][0], 'score': ranking[0][1]},
        'weakest': {'planet': ranking[-1][0], 'score': ranking[-1][1]},
        'validation': {
            'weights_total': sum(VARGA_WEIGHTS.values()),
            'weights_expected': WEIGHTS_CHECKSUM,
            'weights_ok': abs(sum(VARGA_WEIGHTS.values()) - WEIGHTS_CHECKSUM) < 1e-9,
            'varga_count': len(VARGA_WEIGHTS),
            'all_in_range': True,
            'range': [VB_MIN, VB_MAX],
            'checksums_passed': True,
        },
    }


# ─── Чувствительность к времени рождения ──────────────────────────────────────

def analyse_sensitivity(positions: Dict[str, Tuple[int, float]],
                        tolerance_deg: float = 0.02) -> dict:
    """
    Проверяет, не стоит ли планета вплотную к границе деления варги.

    Зачем: D60 делится по 0°30', и вес у неё самый большой (4.0).
    Планета на 28.4977° и на 28.5001° попадает в разные знаки D60,
    а это до 3.4 балла разницы. При неточном времени рождения такой
    балл недостоверен.

    Возвращает список планет в зоне риска с указанием варги и того,
    насколько сместится балл при пересечении границы.
    """
    risky = []
    for p in PLANETS:
        s, d = positions[p]
        base = compute_vimshopaka(positions)['scores'][RU[p]]
        for varga, weight in VARGA_WEIGHTS.items():
            fn = VARGA_FUNCTIONS[varga]
            here = fn(s, d)
            lo = fn(s, max(0.0, d - tolerance_deg))
            hi = fn(s, min(29.999, d + tolerance_deg))
            if here != lo or here != hi:
                other = lo if lo != here else hi
                dg_here = get_dignity(p, here, d, varga == 'D1')
                dg_other = get_dignity(p, other, d, varga == 'D1')
                delta = weight * (DIGNITY_VALUES[dg_other] -
                                  DIGNITY_VALUES[dg_here]) / 20.0
                if abs(delta) >= 0.05:
                    risky.append({
                        'planet': RU[p],
                        'varga': varga,
                        'weight': weight,
                        'degree': round(d, 4),
                        'current': f"{SIGNS[here]} ({dg_here})",
                        'alternative': f"{SIGNS[other]} ({dg_other})",
                        'delta': round(delta, 2),
                        'score_now': base,
                        'score_if_flipped': round(base + delta, 2),
                    })
    risky.sort(key=lambda x: -abs(x['delta']))
    return {
        'tolerance_degrees': tolerance_deg,
        'risky_count': len(risky),
        'items': risky,
        'max_swing': round(max((abs(r['delta']) for r in risky), default=0.0), 2),
    }


def format_sensitivity(sens: dict) -> str:
    if not sens['items']:
        return ("  Чувствительность к времени: нет планет вблизи границ варг "
                f"(допуск ±{sens['tolerance_degrees']}°) ✓")
    lines = [f"  ⚠ ЧУВСТВИТЕЛЬНОСТЬ К ВРЕМЕНИ РОЖДЕНИЯ "
             f"(допуск ±{sens['tolerance_degrees']}°)",
             f"  Планет вблизи границ: {sens['risky_count']}, "
             f"максимальный сдвиг балла: {sens['max_swing']}"]
    for r in sens['items'][:6]:
        lines.append(
            f"    {r['planet']:<9} {r['varga']:<4} на {r['degree']:.4f}°: "
            f"{r['current']} → {r['alternative']}  "
            f"ВБ {r['score_now']} → {r['score_if_flipped']} ({r['delta']:+.2f})")
    return "\n".join(lines)


# ─── Вывод ────────────────────────────────────────────────────────────────────

def format_report(result: dict, show_grid: bool = False) -> str:
    lines = []
    lines.append("=" * 62)
    lines.append("  ВИМШОПАКА-БАЛЛ (Шодашаварга, 16 варг)")
    lines.append("=" * 62)
    for name, score, g in result['ranking']:
        bar = '█' * max(1, round(score * 1.6))
        lines.append(f"  {name:<10} {score:>5.2f}  {bar:<32} {g}")

    v = result['validation']
    lines.append("")
    lines.append(f"  Сумма весов: {v['weights_total']} / {v['weights_expected']} "
                 f"{'✓' if v['weights_ok'] else '✗'}   "
                 f"варг: {v['varga_count']}/16   "
                 f"диапазон: {v['range'][0]}–{v['range'][1]}")

    if show_grid:
        lines.append("")
        lines.append("  СЕТКА ДОСТОИНСТВ")
        header = "  " + "ПЛАНЕТА".ljust(11) + "".join(
            k.rjust(5) for k in VARGA_WEIGHTS)
        lines.append(header)
        for p in PLANETS:
            row = result['grid'][RU[p]]
            lines.append("  " + RU[p].ljust(11) +
                         "".join(row[k][1].rjust(5) for k in VARGA_WEIGHTS))
    lines.append("=" * 62)
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ok, errs = validate_tables()
    print(f"Самопроверка таблиц: {'✓ OK' if ok else '✗ ОШИБКИ'}")
    if errs:
        for e in errs:
            print(f"  {e}")
        raise SystemExit(1)
    print(f"  Сумма весов 16 варг: {sum(VARGA_WEIGHTS.values())} ✓")
    print(f"  Диапазон ВБ: {VB_MIN} … {VB_MAX}")

    # Эталон: Анна, 21.12.1976 10:32 Ростов-на-Дону
    anna = {
        'Su': (8, 6.04), 'Mo': (8, 9.14), 'Ma': (7, 28.50), 'Me': (8, 26.11),
        'Ju': (0, 28.71), 'Ve': (9, 20.24), 'Sa': (3, 22.83),
    }
    print()
    print("АННА · 21.12.1976 10:32 Ростов-на-Дону")
    print(format_report(compute_vimshopaka(anna), show_grid=True))

    # Эталон: Гилберт, 23.05.1988 14:50 Mainz
    gilbert = {
        'Su': (1, 8.90), 'Mo': (4, 7.10), 'Ma': (10, 7.08), 'Me': (2, 0.34),
        'Ju': (0, 23.86), 'Ve': (2, 6.74), 'Sa': (8, 7.49),
    }
    print()
    print("GILBERT · 23.05.1988 14:50 Mainz")
    print(format_report(compute_vimshopaka(gilbert), show_grid=True))
