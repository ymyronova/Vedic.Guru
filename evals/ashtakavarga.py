#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ashtakavarga.py — расчёт Сарваштакаварги (бинду по домам).

⚠️  ПРОИСХОЖДЕНИЕ ТАБЛИЦ И ГРАНИЦЫ ПРИМЕНИМОСТИ  ⚠️
────────────────────────────────────────────────────────────────────────────
Оригинальный ashtakavarga.py, на который ссылается IMPLEMENT.md как на
приложенный, в поставку 29.07.26 не попал. Таблицы BENEFIC_POINTS ниже
воспроизведены из backend/jyotish.py — боевого движка сервиса.

Практическое следствие, которое нельзя забывать:

    Проверка бинду через этот модуль НЕ является независимой.
    Он использует те же таблицы, что и backend/jyotish.py, поэтому
    совпадёт с ним всегда и по построению.

Что это даёт:
  • инвариантные проверки (САВ=337, семь сумм БАВ, диапазон домов)
    работают и здесь — они проверяют целостность самих таблиц;
  • verify_chart.py перестаёт молча пропускать раздел бинду.

Чего это НЕ даёт:
  • eval #12 (эталонные бинду Анны) этим модулем не арбитрируется.
    Наши таблицы дают [24,34,25,27,32,23,21,26,34,38,31,22], эталон —
    [24,35,25,27,31,23,21,26,34,38,31,22]: один бинду смещён ровно на
    3 дома при сохранённой сумме 337. То же расхождение на карте
    Гилберта (дома 7 и 10). Обе стороны проходят все восемь контрольных
    сумм, поэтому checksum-инвариант их не различает, а перебор всех
    одноклеточных замен не нашёл варианта, примиряющего обе карты.
    Разрешить это можно только оригинальным файлом.

Инварианты (не зависят от даты рождения — следуют из самих таблиц):
    сумма САВ по 12 домам = 337
    БАВ: Со 48, Лу 49, Ма 39, Ме 54, Ю 56, Ве 52, Са 39
"""

from typing import Dict, List, Tuple

# ─── Константы ────────────────────────────────────────────────────────────────

PLANETS = ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa']
CONTRIBUTORS = ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'As']  # + лагна

RU = {'Su': 'Солнце', 'Mo': 'Луна', 'Ma': 'Марс', 'Me': 'Меркурий',
      'Ju': 'Юпитер', 'Ve': 'Венера', 'Sa': 'Сатурн', 'As': 'Лагна'}

SIGNS = ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева',
         'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы']

# Пороги интерпретации. IMPLEMENT.md: не менять без согласования —
# на них завязаны формулировки в отчётах.
BINDU_STRONG = 30
BINDU_NORMAL = 25
BINDU_MIN, BINDU_MAX = 18, 42        # эмпирическое правило, НЕ инвариант

SAV_CHECKSUM = 337
SAV_AVERAGE = 28                     # 337/12 = 28.08 → целое для vs_average

BAV_CHECKSUMS = {'Su': 48, 'Mo': 49, 'Ma': 39, 'Me': 54,
                 'Ju': 56, 'Ve': 52, 'Sa': 39}

# Дома от каждого контрибутора, дающие бинду. НЕ ПРАВИТЬ:
# выверено по контрольным суммам, любая «оптимизация» их ломает.
BENEFIC_POINTS: Dict[str, Dict[str, List[int]]] = {
 "Su": {"Su": [1,2,4,7,8,9,10,11], "Mo": [3,6,10,11], "Ma": [1,2,4,7,8,9,10,11],
        "Me": [3,5,6,9,10,11,12], "Ju": [5,6,9,11], "Ve": [6,7,12],
        "Sa": [1,2,4,7,8,9,10,11], "As": [3,4,6,10,11,12]},
 "Mo": {"Su": [3,6,7,8,10,11], "Mo": [1,3,6,7,10,11], "Ma": [2,3,5,6,9,10,11],
        "Me": [1,3,4,5,7,8,10,11], "Ju": [1,2,4,7,8,10,11], "Ve": [3,4,5,7,9,10,11],
        "Sa": [3,5,6,11], "As": [3,6,10,11]},
 "Ma": {"Su": [3,5,6,10,11], "Mo": [3,6,11], "Ma": [1,2,4,7,8,10,11],
        "Me": [3,5,6,11], "Ju": [6,10,11,12], "Ve": [6,8,11,12],
        "Sa": [1,4,7,8,9,10,11], "As": [1,3,6,10,11]},
 "Me": {"Su": [5,6,9,11,12], "Mo": [2,4,6,8,10,11], "Ma": [1,2,4,7,8,9,10,11],
        "Me": [1,3,5,6,9,10,11,12], "Ju": [6,8,11,12], "Ve": [1,2,3,4,5,8,9,11],
        "Sa": [1,2,4,7,8,9,10,11], "As": [1,2,4,6,8,10,11]},
 "Ju": {"Su": [1,2,3,4,7,8,9,10,11], "Mo": [2,5,7,9,11], "Ma": [1,2,4,7,8,10,11],
        "Me": [1,2,4,5,6,9,10,11], "Ju": [1,2,3,4,7,8,10,11], "Ve": [2,5,6,9,10,11],
        "Sa": [3,5,6,12], "As": [1,2,4,5,6,7,9,10,11]},
 "Ve": {"Su": [8,11,12], "Mo": [1,2,3,4,5,8,9,11,12], "Ma": [3,5,6,9,11,12],
        "Me": [3,5,6,9,11], "Ju": [5,8,9,10,11], "Ve": [1,2,3,4,5,8,9,10,11],
        "Sa": [3,4,5,8,9,10,11], "As": [1,2,3,4,5,8,9,11]},
 "Sa": {"Su": [1,2,4,7,8,10,11], "Mo": [3,6,11], "Ma": [3,5,6,10,11,12],
        "Me": [6,8,9,10,11,12], "Ju": [5,6,11,12], "Ve": [6,11,12],
        "Sa": [3,5,6,11], "As": [1,3,4,6,10,11]},
}


class AshtakavargaChecksumError(Exception):
    """Контрольная сумма не сошлась — результату доверять нельзя."""
    pass


# ─── Самопроверка таблиц ──────────────────────────────────────────────────────

def validate_tables() -> Tuple[bool, List[str]]:
    """Проверяет инварианты таблиц. Вызывается при импорте.

    Суммы БАВ и САВ не зависят от карты: они равны количеству записей в
    таблицах. Поэтому повреждение таблиц ловится здесь, до любого расчёта.
    """
    errors = []

    if set(BENEFIC_POINTS) != set(PLANETS):
        errors.append(f"Планеты в таблицах {sorted(BENEFIC_POINTS)}, ожидается {PLANETS}")

    grand_total = 0
    for p in PLANETS:
        row = BENEFIC_POINTS.get(p, {})
        if set(row) != set(CONTRIBUTORS):
            errors.append(f"{RU[p]}: контрибуторы {sorted(row)}, ожидается {CONTRIBUTORS}")
            continue
        total = 0
        for c in CONTRIBUTORS:
            houses = row[c]
            if len(set(houses)) != len(houses):
                errors.append(f"{RU[p]}/{RU[c]}: дубликаты домов {houses}")
            bad = [h for h in houses if not 1 <= h <= 12]
            if bad:
                errors.append(f"{RU[p]}/{RU[c]}: дома вне 1–12: {bad}")
            total += len(houses)
        grand_total += total
        expected = BAV_CHECKSUMS[p]
        if total != expected:
            errors.append(f"БАВ {RU[p]}: {total}, ожидается {expected}")

    if grand_total != SAV_CHECKSUM:
        errors.append(f"Сумма САВ {grand_total}, ожидается {SAV_CHECKSUM}")

    if sum(BAV_CHECKSUMS.values()) != SAV_CHECKSUM:
        errors.append(f"Сумма контрольных БАВ {sum(BAV_CHECKSUMS.values())}, "
                      f"ожидается {SAV_CHECKSUM}")

    return len(errors) == 0, errors


_ok, _errs = validate_tables()
if not _ok:
    raise AshtakavargaChecksumError(
        "Таблицы Аштакаварги повреждены:\n  " + "\n  ".join(_errs))


# ─── Основной расчёт ──────────────────────────────────────────────────────────

def _grade(bindu: int) -> str:
    if bindu >= BINDU_STRONG:
        return 'сильный'
    if bindu >= BINDU_NORMAL:
        return 'норма'
    return 'уязвимый'


def compute_ashtakavarga(sign_indices: Dict[str, int], lagna_sign_idx: int) -> dict:
    """Считает БАВ каждой планеты и САВ по домам.

    Аргументы:
        sign_indices:    {'Su': 8, 'Mo': 8, ...} — индекс знака 0–11 для 7 грах.
                         Раху и Кету не участвуют: в классической Аштакаварге
                         узлы не учитываются.
        lagna_sign_idx:  индекс знака лагны 0–11.
    """
    for p in PLANETS:
        if p not in sign_indices:
            raise ValueError(f"Не передана позиция: {RU[p]} ({p})")
        s = sign_indices[p]
        if not isinstance(s, int) or not 0 <= s <= 11:
            raise ValueError(f"{RU[p]}: индекс знака {s} вне 0–11")
    if not isinstance(lagna_sign_idx, int) or not 0 <= lagna_sign_idx <= 11:
        raise ValueError(f"Лагна: индекс знака {lagna_sign_idx} вне 0–11")

    pos = dict(sign_indices)
    pos['As'] = lagna_sign_idx

    # БАВ каждой планеты: бинду по знакам 0–11
    bav: Dict[str, List[int]] = {}
    for p in PLANETS:
        b = [0] * 12
        for c in CONTRIBUTORS:
            for h in BENEFIC_POINTS[p][c]:
                b[(pos[c] + h - 1) % 12] += 1
        bav[p] = b

    bav_totals = {RU[p]: sum(bav[p]) for p in PLANETS}

    # САВ по знакам, затем по домам от лагны
    sav_sign = [sum(bav[p][i] for p in PLANETS) for i in range(12)]
    sav_by_house = [sav_sign[(lagna_sign_idx + h - 1) % 12] for h in range(1, 13)]

    sav_total = sum(sav_by_house)
    sav_ok = sav_total == SAV_CHECKSUM
    bav_bad = {RU[p]: sum(bav[p]) for p in PLANETS if sum(bav[p]) != BAV_CHECKSUMS[p]}
    bav_all_ok = not bav_bad

    if not (sav_ok and bav_all_ok):
        raise AshtakavargaChecksumError(
            f"Контрольная сумма не сошлась: САВ {sav_total} "
            f"(ожидается {SAV_CHECKSUM})"
            + (f"; БАВ расходятся: {bav_bad}" if bav_bad else ""))

    houses = [{
        'house': h,
        'sign': SIGNS[(lagna_sign_idx + h - 1) % 12],
        'bindu': sav_by_house[h - 1],
        'grade': _grade(sav_by_house[h - 1]),
        'vs_average': sav_by_house[h - 1] - SAV_AVERAGE,
    } for h in range(1, 13)]

    strongest = max(houses, key=lambda x: x['bindu'])
    weakest = min(houses, key=lambda x: x['bindu'])
    out_of_range = [h['house'] for h in houses
                    if not BINDU_MIN <= h['bindu'] <= BINDU_MAX]

    return {
        'bav': bav,
        'bav_totals': bav_totals,
        'sav_by_sign': sav_sign,
        'sav_by_house': sav_by_house,
        'houses': houses,
        'strongest_house': {'house': strongest['house'], 'bindu': strongest['bindu']},
        'weakest_house': {'house': weakest['house'], 'bindu': weakest['bindu']},
        'validation': {
            'sav_total': sav_total,
            'sav_expected': SAV_CHECKSUM,
            'sav_ok': sav_ok,
            'bav_totals': bav_totals,
            'bav_expected': {RU[p]: v for p, v in BAV_CHECKSUMS.items()},
            'bav_all_ok': bav_all_ok,
            'checksums_passed': sav_ok and bav_all_ok,
            # Диапазон 18–42 — эмпирическое правило, а не инвариант: карта
            # Токио 09.09.2010 даёт 17 в 12-м доме при корректной сумме 337.
            # Поэтому он сообщается, но не роняет расчёт.
            'houses_out_of_range': out_of_range,
            'range': [BINDU_MIN, BINDU_MAX],
            'independent_of_service_engine': False,
        },
    }


# ─── Вывод ────────────────────────────────────────────────────────────────────

def format_report(result: dict) -> str:
    lines = ["=" * 62,
             "  САРВАШТАКАВАРГА — БИНДУ ПО ДОМАМ",
             "=" * 62]
    for h in result['houses']:
        bar = '█' * max(1, round(h['bindu'] / 3))
        mark = ''
        if h['house'] == result['strongest_house']['house']:
            mark = ' ★'
        elif h['house'] == result['weakest_house']['house']:
            mark = ' ▼'
        lines.append(f"  {h['house']:>2}  {h['sign']:<11} {h['bindu']:>2}  "
                     f"{bar:<14} {h['grade']}{mark}")
    v = result['validation']
    status = '✓' if v['checksums_passed'] else '✗'
    lines.append("")
    lines.append(f"  Сумма {v['sav_total']} / {v['sav_expected']} {status}   "
                 f"среднее {v['sav_total']/12:.1f}")
    lines.append("  БАВ: " + ", ".join(f"{k} {x}" for k, x in v['bav_totals'].items()))
    if v['houses_out_of_range']:
        lines.append(f"  ⚠ вне диапазона {v['range']}: дома {v['houses_out_of_range']} "
                     f"(правило эмпирическое, не инвариант)")
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
    print(f"  Контрольная сумма САВ: {SAV_CHECKSUM} ✓")
    print("  Контрольные суммы БАВ: "
          + ", ".join(f"{RU[p]} {v}" for p, v in BAV_CHECKSUMS.items()) + " ✓")
    print("  ⚠ Таблицы воспроизведены из backend/jyotish.py — сверка бинду")
    print("    этим модулем НЕ независима (см. шапку файла, eval #12).")

    # Эталон: Анна, 21.12.1976 10:32 Ростов-на-Дону — лагна Козерог (9)
    anna = {'Su': 8, 'Mo': 8, 'Ma': 7, 'Me': 8, 'Ju': 0, 'Ve': 9, 'Sa': 3}
    print()
    print("АННА · 21.12.1976 10:32 Ростов-на-Дону · лагна Козерог")
    print(format_report(compute_ashtakavarga(anna, 9)))
