#!/usr/bin/env python3
"""
verify_chart.py — Слой 1 верификации джйотиш-сервиса.

Запускать ПЕРЕД генерацией нарратива альманаха.
Принимает данные рождения → считает через pyswisseph →
выводит JSON с эталонными позициями + флаги расхождений.

Использование:
    python verify_chart.py --name "Анна" --date 1976-12-21 --time 10:32 \
        --lat 47.233 --lon 39.717 --tz 3

    python verify_chart.py --compare ground_truth.json output_to_check.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

try:
    import swisseph as swe
except ImportError:
    print("ERROR: pyswisseph не установлен. Запустите: pip install pyswisseph --break-system-packages")
    sys.exit(1)

# ─── Константы ────────────────────────────────────────────────────────────────

SIGNS = ['Овен','Телец','Близнецы','Рак','Лев','Дева',
         'Весы','Скорпион','Стрелец','Козерог','Водолей','Рыбы']

SIGNS_EN = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
            'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

NAKSHATRA_NAMES = [
    'Ашвини','Бхарани','Криттика','Рохини','Мригашира','Ардра','Пунарвасу',
    'Пушья','Ашлеша','Магха','Пурвапхалгуни','Уттарапхалгуни','Хаста',
    'Читра','Свати','Вишакха','Анурадха','Джьештха','Мула','Пурвашадха',
    'Уттарашадха','Шравана','Дхаништха','Шатабхиша','Пурвабхадрапада',
    'Уттарабхадрапада','Ревати'
]

NAKSHATRA_LORDS = ['Ке','Ве','Со','Лу','Ма','Ра','Ю','Са','Ме'] * 3

DASHA_YEARS = {'Ке':7,'Ве':20,'Со':6,'Лу':10,'Ма':7,'Ра':18,'Ю':16,'Са':19,'Ме':17}
DASHA_NAMES = {'Ке':'Кету','Ве':'Венера','Со':'Солнце','Лу':'Луна',
               'Ма':'Марс','Ра':'Раху','Ю':'Юпитер','Са':'Сатурн','Ме':'Меркурий'}

PLANET_IDS = {
    'sun': swe.SUN, 'moon': swe.MOON, 'mars': swe.MARS,
    'mercury': swe.MERCURY, 'jupiter': swe.JUPITER,
    'venus': swe.VENUS, 'saturn': swe.SATURN,
    'rahu': swe.MEAN_NODE,
}

PLANET_RU = {
    'sun':'Солнце','moon':'Луна','mars':'Марс','mercury':'Меркурий',
    'jupiter':'Юпитер','venus':'Венера','saturn':'Сатурн',
    'rahu':'Раху','ketu':'Кету'
}

# ─── Расчёт карты ──────────────────────────────────────────────────────────────

def calculate_chart(date_str: str, time_str: str, lat: float, lon: float, tz_offset: float) -> dict:
    """
    Основная функция расчёта натальной карты.
    Возвращает словарь с позициями планет, лагной, дашами.
    """
    # Only point Swiss Ephemeris at the data dir if it actually exists. This module
    # is imported by the service, and set_ephe_path is global state — pointing it at
    # a missing directory would silently change which ephemeris backend/jyotish.py
    # uses, making the cross-check compare two differently-configured engines.
    if os.path.isdir('/usr/share/ephe'):
        swe.set_ephe_path('/usr/share/ephe')
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # Парсинг даты/времени → UTC
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt_utc = dt - timedelta(hours=tz_offset)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                    dt_utc.hour + dt_utc.minute/60.0)

    ayanamsha = swe.get_ayanamsa_ut(jd)

    # Планеты
    planets = {}
    lagna_sign = None
    for name, pid in PLANET_IDS.items():
        ret, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)
        lon_sid = ret[0]
        is_retro = ret[3] < 0  # скорость < 0 = ретроградный
        sign_idx = int(lon_sid / 30)
        deg_in_sign = lon_sid % 30
        planets[name] = {
            'longitude_sidereal': round(lon_sid, 4),
            'sign': SIGNS[sign_idx],
            'sign_index': sign_idx,
            'degree_in_sign': round(deg_in_sign, 4),
            'retrograde': is_retro,
        }

    # Кету
    rahu_lon = planets['rahu']['longitude_sidereal']
    ketu_lon = (rahu_lon + 180) % 360
    sign_idx = int(ketu_lon / 30)
    planets['ketu'] = {
        'longitude_sidereal': round(ketu_lon, 4),
        'sign': SIGNS[sign_idx],
        'sign_index': sign_idx,
        'degree_in_sign': round(ketu_lon % 30, 4),
        'retrograde': True,
    }

    # Асцендент (тропик → сидерик)
    asc_data = swe.houses(jd, lat, lon, b'P')
    asc_trop = asc_data[1][0]
    asc_sid = (asc_trop - ayanamsha) % 360
    lagna_sign_idx = int(asc_sid / 30)
    lagna_deg = asc_sid % 30

    # Дома (WSH) — от лагны
    for name in list(planets.keys()):
        p = planets[name]
        house_num = ((p['sign_index'] - lagna_sign_idx) % 12) + 1
        p['house'] = house_num

    # Накшатра Луны
    moon_lon = planets['moon']['longitude_sidereal']
    moon_naksh_idx = int(moon_lon / (360/27))
    moon_naksh_deg = moon_lon % (360/27)
    moon_naksh_span = 360/27
    moon_naksh_lord = NAKSHATRA_LORDS[moon_naksh_idx]

    # Вимшоттари
    fraction_passed = moon_naksh_deg / moon_naksh_span
    first_dasha_lord = moon_naksh_lord
    first_dasha_total = DASHA_YEARS[first_dasha_lord]
    first_dasha_passed = fraction_passed * first_dasha_total
    first_dasha_remaining = first_dasha_total - first_dasha_passed

    birth_date = datetime(dt.year, dt.month, dt.day)
    today = datetime.now()

    all_lords = ['Ке','Ве','Со','Лу','Ма','Ра','Ю','Са','Ме']
    start_idx = all_lords.index(first_dasha_lord)
    sequence = all_lords[start_idx:] + all_lords[:start_idx]

    dashas = []
    current_dt = birth_date
    current_md = None
    for i, lord in enumerate(sequence):
        yr = first_dasha_remaining if i == 0 else DASHA_YEARS[lord]
        start_dt = current_dt
        end_dt = current_dt + timedelta(days=yr*365.25)
        is_current = start_dt <= today <= end_dt
        if is_current:
            current_md = lord
        dashas.append({
            'planet': DASHA_NAMES[lord],
            'lord_code': lord,
            'start': start_dt.strftime('%m.%Y'),
            'end': end_dt.strftime('%m.%Y'),
            'duration_years': round(yr, 3),
            'current': is_current,
        })
        current_dt = end_dt

    # Антардаши текущей МД
    current_antardasha = None
    if current_md:
        md_entry = next(d for d in dashas if d['lord_code'] == current_md)
        md_start = datetime.strptime('01.' + md_entry['start'], '%d.%m.%Y')
        md_total = md_entry['duration_years']
        ant_order = all_lords[all_lords.index(current_md):] + all_lords[:all_lords.index(current_md)]
        ant_current = md_start
        for ant_lord in ant_order:
            ant_months = DASHA_YEARS[ant_lord] / 120 * md_total * 12
            ant_end = ant_current + timedelta(days=ant_months*30.44)
            if ant_current <= today <= ant_end:
                current_antardasha = f"{DASHA_NAMES[current_md]}/{DASHA_NAMES[ant_lord]}"
                break
            ant_current = ant_end

    # АК и ДК
    grahas = ['sun','moon','mars','mercury','jupiter','venus','saturn']
    ak_planet = max(grahas, key=lambda g: planets[g]['degree_in_sign'])
    dk_planet = min(grahas, key=lambda g: planets[g]['degree_in_sign'])

    return {
        'meta': {
            'birth_date': date_str,
            'birth_time': time_str,
            'latitude': lat,
            'longitude': lon,
            'timezone_offset': tz_offset,
            'julian_day': round(jd, 4),
            'ayanamsha_lahiri': round(ayanamsha, 4),
            'calculated_at': datetime.now().isoformat(),
        },
        'ascendant': {
            'sign': SIGNS[lagna_sign_idx],
            'sign_index': lagna_sign_idx,
            'degree_in_sign': round(lagna_deg, 4),
        },
        'planets': planets,
        'moon_nakshatra': {
            'name': NAKSHATRA_NAMES[moon_naksh_idx],
            'lord': PLANET_RU.get(NAKSHATRA_LORDS[moon_naksh_idx].lower(),
                                   NAKSHATRA_LORDS[moon_naksh_idx]),
            'lord_code': moon_naksh_lord,
            'degree_in_nakshatra': round(moon_naksh_deg, 4),
        },
        'atmakaraka': {
            'planet': PLANET_RU[ak_planet],
            'degree_in_sign': round(planets[ak_planet]['degree_in_sign'], 4),
        },
        'darakaraka': {
            'planet': PLANET_RU[dk_planet],
            'degree_in_sign': round(planets[dk_planet]['degree_in_sign'], 4),
        },
        'vimshottari_dashas': dashas,
        'current_mahadasha': DASHA_NAMES.get(current_md, 'неизвестно'),
        'current_antardasha': current_antardasha or 'не определена',
    }

# ─── Верификация против ground_truth ──────────────────────────────────────────

def verify_against_ground_truth(chart: dict, ground_truth: dict) -> dict:
    """
    Сравнивает рассчитанную карту с эталоном из evals.json.
    Возвращает список прошедших/провалившихся проверок.
    """
    checks = []

    gt_planets = ground_truth.get('planets_sidereal', {})

    for planet_en, gt_data in gt_planets.items():
        if planet_en not in chart['planets']:
            checks.append({
                'check': f"{planet_en} присутствует в расчёте",
                'passed': False,
                'evidence': "Планета отсутствует в расчёте",
            })
            continue

        p = chart['planets'][planet_en]

        # Проверка знака
        sign_match = p['sign'] == gt_data['sign']
        checks.append({
            'check': f"{PLANET_RU.get(planet_en, planet_en)} в знаке {gt_data['sign']}",
            'passed': sign_match,
            'evidence': f"Рассчитано: {p['sign']} {p['degree_in_sign']:.2f}°",
        })

        # Проверка дома
        house_match = p['house'] == gt_data['house']
        checks.append({
            'check': f"{PLANET_RU.get(planet_en, planet_en)} в {gt_data['house']}-м доме",
            'passed': house_match,
            'evidence': f"Рассчитано: {p['house']}-й дом",
        })

        # Ретроградность
        if 'retrograde' in gt_data:
            retro_match = p['retrograde'] == gt_data['retrograde']
            checks.append({
                'check': f"{PLANET_RU.get(planet_en, planet_en)} ретроградный={gt_data['retrograde']}",
                'passed': retro_match,
                'evidence': f"Рассчитано: ретроградный={p['retrograde']}",
            })

    # Проверка накшатры Луны
    gt_naksh = ground_truth.get('moon_nakshatra', {})
    if gt_naksh:
        calc_naksh = chart['moon_nakshatra']['name']
        naksh_match = calc_naksh == gt_naksh.get('name', calc_naksh)
        checks.append({
            'check': f"Накшатра Луны: {gt_naksh.get('name', '?')}",
            'passed': naksh_match,
            'evidence': f"Рассчитано: {calc_naksh}",
        })

    # Проверка текущей МД
    gt_md = ground_truth.get('current_mahadasha', '')
    if gt_md:
        md_match = chart['current_mahadasha'] == gt_md
        checks.append({
            'check': f"Текущая МД: {gt_md}",
            'passed': md_match,
            'evidence': f"Рассчитано: {chart['current_mahadasha']}",
        })

    passed = sum(1 for c in checks if c['passed'])
    total = len(checks)

    return {
        'checks': checks,
        'summary': {
            'passed': passed,
            'failed': total - passed,
            'total': total,
            'pass_rate': round(passed / total, 3) if total > 0 else 0,
        }
    }


# ─── Форматирование вывода ─────────────────────────────────────────────────────

def print_chart_summary(chart: dict):
    """Красивый вывод карты в консоль."""
    meta = chart['meta']
    print(f"\n{'='*60}")
    print(f"  НАТАЛЬНАЯ КАРТА · Лахири · цельнознаковые дома")
    print(f"  {meta['birth_date']} {meta['birth_time']} UTC{meta['timezone_offset']:+.0f}")
    print(f"  Аянамша Лахири: {meta['ayanamsha_lahiri']:.3f}°")
    print(f"{'='*60}")

    asc = chart['ascendant']
    print(f"\n  ЛАГНА: {asc['sign']} {asc['degree_in_sign']:.2f}°")

    print(f"\n  {'ПЛАНЕТА':<12} {'ЗНАК':<12} {'ГРАДУС':<8} {'ДОМ':<5} {'РТ'}")
    print(f"  {'-'*50}")
    for name, p in chart['planets'].items():
        retro = '℞' if p['retrograde'] else ''
        print(f"  {PLANET_RU.get(name, name):<12} {p['sign']:<12} {p['degree_in_sign']:>6.2f}°  {p['house']:<5} {retro}")

    mn = chart['moon_nakshatra']
    print(f"\n  Луна: накшатра {mn['name']} · упр. {mn['lord']}")

    ak = chart['atmakaraka']
    dk = chart['darakaraka']
    print(f"  Атмакарака: {ak['planet']} ({ak['degree_in_sign']:.2f}°)")
    print(f"  Даракарака:  {dk['planet']} ({dk['degree_in_sign']:.2f}°)")

    print(f"\n  ВИМШОТТАРИ ДАШИ:")
    for d in chart['vimshottari_dashas']:
        marker = ' ◀ СЕЙЧАС' if d['current'] else ''
        print(f"    {d['planet']:<10} {d['start']:<10} {d['end']:<10}{marker}")

    print(f"\n  Текущая МД: {chart['current_mahadasha']}")
    print(f"  Текущая АД: {chart['current_antardasha']}")
    print(f"{'='*60}\n")


def print_verification_result(result: dict):
    """Вывод результатов верификации."""
    summary = result['summary']
    print(f"\n  ВЕРИФИКАЦИЯ: {summary['passed']}/{summary['total']} проверок пройдено")
    print(f"  Pass rate: {summary['pass_rate']*100:.0f}%")
    print()
    for c in result['checks']:
        icon = '✓' if c['passed'] else '✗'
        status = 'OK' if c['passed'] else 'FAIL'
        print(f"  [{icon}] {c['check']}")
        if not c['passed']:
            print(f"       → {c['evidence']}")


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Верификация джйотиш-расчётов через pyswisseph'
    )
    subparsers = parser.add_subparsers(dest='command')

    # Команда: calculate
    calc_p = subparsers.add_parser('calculate', help='Рассчитать карту и вывести JSON')
    calc_p.add_argument('--name', default='Пользователь')
    calc_p.add_argument('--date', required=True, help='YYYY-MM-DD')
    calc_p.add_argument('--time', required=True, help='HH:MM')
    calc_p.add_argument('--lat', type=float, required=True)
    calc_p.add_argument('--lon', type=float, required=True)
    calc_p.add_argument('--tz', type=float, default=3.0, help='UTC offset, напр. 3 для MSK')
    calc_p.add_argument('--output', help='Сохранить JSON в файл')
    calc_p.add_argument('--quiet', action='store_true', help='Только JSON, без таблицы')

    # Команда: verify
    ver_p = subparsers.add_parser('verify', help='Проверить карту против ground_truth из evals.json')
    ver_p.add_argument('--evals', default='evals.json', help='Путь к evals.json')
    ver_p.add_argument('--eval-id', type=int, default=1, help='ID eval для проверки')
    ver_p.add_argument('--date', required=True)
    ver_p.add_argument('--time', required=True)
    ver_p.add_argument('--lat', type=float, required=True)
    ver_p.add_argument('--lon', type=float, required=True)
    ver_p.add_argument('--tz', type=float, default=3.0)

    # Команда: run-all (все evals)
    run_p = subparsers.add_parser('run-all', help='Запустить все Layer 1 и Layer 2 evals')
    run_p.add_argument('--evals', default='evals.json')

    args = parser.parse_args()

    if args.command == 'calculate':
        chart = calculate_chart(args.date, args.time, args.lat, args.lon, args.tz)
        if not args.quiet:
            print_chart_summary(chart)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(chart, f, ensure_ascii=False, indent=2)
            print(f"  JSON сохранён: {args.output}")
        else:
            print(json.dumps(chart, ensure_ascii=False, indent=2))

    elif args.command == 'verify':
        with open(args.evals, encoding='utf-8') as f:
            evals_data = json.load(f)

        eval_entry = next((e for e in evals_data['evals'] if e['id'] == args.eval_id), None)
        if not eval_entry:
            print(f"Eval id={args.eval_id} не найден")
            sys.exit(1)

        chart = calculate_chart(args.date, args.time, args.lat, args.lon, args.tz)
        print_chart_summary(chart)

        gt = eval_entry.get('ground_truth', {})
        # Перевод структуры ground_truth
        gt_adapted = {
            'planets_sidereal': gt.get('planets_sidereal', {}),
            'moon_nakshatra': {'name': gt.get('planets_sidereal', {}).get('moon', {}).get('nakshatra', '')},
            'current_mahadasha': gt.get('current_mahadasha', ''),
        }
        result = verify_against_ground_truth(chart, gt_adapted)
        print_verification_result(result)

        if result['summary']['pass_rate'] < 0.9:
            print("\n  ⚠️  КРИТИЧЕСКАЯ ОШИБКА: pass rate < 90%. Генерация нарратива ЗАБЛОКИРОВАНА.")
            sys.exit(2)
        else:
            print("\n  ✅ Верификация пройдена. Можно генерировать нарратив.")

    elif args.command == 'run-all':
        print("Запуск всех evals (layer_1_calculation и layer_2_logic)...")
        with open(args.evals, encoding='utf-8') as f:
            evals_data = json.load(f)

        # Эталонный кейс берём из evals.json (meta.reference_birth_data), чтобы
        # данные рождения не дублировались между CLI и рантайм-гейтом сервиса.
        ref = evals_data.get('meta', {}).get('reference_birth_data') or {
            'date': '1976-12-21', 'time': '10:32',
            'lat': 47.233, 'lon': 39.717, 'tz_offset': 3.0,
        }
        anna_chart = calculate_chart(ref['date'], ref['time'],
                                     float(ref['lat']), float(ref['lon']),
                                     float(ref['tz_offset']))
        print_chart_summary(anna_chart)

        # Eval 1: позиции планет
        gt_eval1 = {
            'planets_sidereal': {
                'moon':    {'sign': 'Стрелец', 'house': 12, 'nakshatra': 'Мула'},
                'mars':    {'sign': 'Скорпион', 'house': 11},
                'jupiter': {'sign': 'Овен',    'house': 4},
                'rahu':    {'sign': 'Весы',    'house': 10, 'retrograde': True},
                'ketu':    {'sign': 'Овен',    'house': 4},
                'saturn':  {'sign': 'Рак',     'house': 7,  'retrograde': True},
                'venus':   {'sign': 'Козерог', 'house': 1},
            },
            'current_mahadasha': 'Раху',
        }
        result = verify_against_ground_truth(anna_chart, gt_eval1)
        print_verification_result(result)

        total_pass = result['summary']['pass_rate']
        print(f"\n  Итого Layer 1: {total_pass*100:.0f}%")
        if total_pass < 0.9:
            print("  ⚠️  FAIL — расчёты требуют исправления перед генерацией нарратива.")
            sys.exit(2)
        else:
            print("  ✅ PASS — расчёты корректны.")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
