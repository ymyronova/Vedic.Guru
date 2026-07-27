# -*- coding: utf-8 -*-
"""
Interpretation layer. Turns the deterministic chart numbers into Russian prose.

If ANTHROPIC_API_KEY is set, uses the Claude API (recommended — this is what makes
the almanac feel alive). If not, falls back to concise template text so the app
still runs end-to-end for local testing.

Design rule: Claude is given the *already computed* facts and told never to invent
numbers — every figure in the prose comes from the engine, not the model.
"""
from __future__ import annotations
import os, json

MODEL = os.environ.get("JYOTISH_MODEL", "claude-sonnet-5")

SYSTEM = """Ты — сервис «Джйотиш-Альманах». Пиши ВСЕГДА на русском, тёплым, точным,
образным языком. Это символический интерпретативный материал — не предсказание,
не медицинское и не психологическое суждение о человеке. Никогда не выдумывай
числовые значения: используй только те факты и числа, что переданы во входных
данных. Не осуждай человека, слабые места описывай как зоны роста. Пиши прозой,
без маркированных списков внутри секций."""

def _facts(chart: dict) -> str:
    a = chart["ascendant"]
    lines = [f"Лагна: {a['sign_ru']} {a['dms']}, накшатра {a['nakshatra']} пада {a['pada']}."]
    lines.append("Планеты (знак, дом, дом.№, накшатра, достоинство D1, ретро):")
    for k, pl in chart["planets"].items():
        lines.append(f"  {pl['name']}: {pl['sign_ru']} {pl['dms']}, дом {pl['house']}, "
                     f"накшатра {pl['nakshatra']}, достоинство {pl['dignity']}"
                     + (", ретроградна" if pl['retro'] else ""))
    lines.append("Вимшопака-балл (из 20): " + ", ".join(f"{chart['planets'][k]['name']} {v}" for k,v in chart['vb'].items()))
    lines.append("Бинду по домам (SAV, среднее %s): " % chart['sav_avg'] +
                 ", ".join(f"дом {h}={v}" for h,v in chart['sav_house'].items()))
    kk = chart["karakas"]
    lines.append(f"Атмакарака: {kk['Атмакарака']['pl_ru']}; Даракарака: {kk['Даракарака']['pl_ru']}; "
                 f"Каракамса (навамша-знак Атмакараки): {chart['karakamsa']}.")
    cd = chart["current_dasha"]
    ad = next((x for x in chart["antardashas"] if x["current"]), None)
    lines.append(f"Текущая махадаша: {cd['lord_ru']} ({cd['start'].year}–{cd['end'].year}), "
                 f"антардаша: {ad['lord_ru'] if ad else '—'}.")
    lines.append("Обнаруженные йоги: " + "; ".join(f"{y['name']} — {y['mech']}" for y in chart["yogas"]))
    return "\n".join(lines)

_INSTRUCT = """На основе фактов карты напиши JSON строго с этими ключами (только JSON, без пояснений):
{
 "portrait": "Раздел 1 «Портрет одной нитью» — один плотный абзац (4–6 предложений): лагна и её тема, Атмакарака и Каракамса, сильнейшие планеты по Вимшопаке, сильнейшее и слабейшее поле (по бинду), дуга жизни одной фразой.",
 "shodashavarga": "Раздел 2 — 2–3 абзаца: какая планета рабочий инструмент и почему, парадокс между Атмакаракой и операционными силами, что это значит для стратегии; затем разбор сильных и слабых домов по бинду.",
 "yogas": "Раздел 3 — по абзацу на каждую обнаруженную йогу: механизм простыми словами, что активирует в жизни, оценка силы.",
 "dasha": "Раздел 4 — обзор дуги жизни по махадашам с качественной оценкой каждой и особенно подробно про текущую махадашу и антардашу: что это за окно, какие сферы активны.",
 "integral": "Раздел 5 «Итоговая картина» — 3 абзаца: тип судьбы (сильный игрок/сильное поле/оба/ни то), главная формула жизни, единственная подлинная ахиллесова пята.",
 "planets": "Раздел 6 — для каждой из 7 планет короткий блок из 3–4 фраз: состояние в карте, высшее состояние (что активирует лучшее), раджа-активатор, чего избегать. Верни как один связный текст с подзаголовками-планетами."
}"""

def generate_almanac(chart: dict) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _fallback(chart)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=MODEL, max_tokens=4000, system=SYSTEM,
            messages=[{"role":"user","content": _facts(chart) + "\n\n" + _INSTRUCT}],
        )
        text = "".join(b.text for b in msg.content if getattr(b,"type",None)=="text")
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        out = _fallback(chart); out["_note"] = f"Claude недоступен ({e}); показан шаблон."
        return out

def rectify_description(chart: dict) -> dict:
    """Step-1 lagna description + two neighbours. Uses Claude if available, else template."""
    a = chart["ascendant"]; key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"main": f"Восходящий знак — {a['sign_ru']} ({a['dms']}), накшатра {a['nakshatra']}. "
                        "Подключите ANTHROPIC_API_KEY для развёрнутого описания лагны и соседних знаков.",
                "confirm": "Узнаёте ли вы себя в этом знаке?"}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        prompt = (f"Восходящий знак — {a['sign_ru']} {a['dms']}, накшатра {a['nakshatra']} пада {a['pada']}, "
                  f"в 1-м доме планеты: "
                  + (", ".join(p['name'] for k,p in chart['planets'].items() if p['house']==1) or "нет") + ". "
                  "Опиши эту лагну развёрнуто и конкретно (внешность, темперамент, паттерн поведения, "
                  "отношение к жизни), затем для контраста кратко опиши предыдущий и следующий знаки зодиака "
                  "как восходящие. Заверши вопросом, узнаёт ли человек себя. Пиши на русском.")
        msg = client.messages.create(model=MODEL, max_tokens=1500, system=SYSTEM,
                                      messages=[{"role":"user","content":prompt}])
        text = "".join(b.text for b in msg.content if getattr(b,"type",None)=="text")
        return {"main": text, "confirm": "Узнаёте ли вы себя в этом описании?"}
    except Exception as e:
        return {"main": f"Восходящий знак — {a['sign_ru']} {a['dms']}. (Claude недоступен: {e})",
                "confirm": "Узнаёте ли вы себя в этом знаке?"}

# --------------------------- template fallback ---------------------------
def _fallback(chart: dict) -> dict:
    vb = chart["vb"]; strongest = max(vb, key=vb.get)
    from jyotish import PL_RU
    sav = chart["sav_house"]
    best_house = max(sav, key=sav.get); worst_house = min(sav, key=sav.get)
    a = chart["ascendant"]; kk = chart["karakas"]
    yoga_txt = " ".join(f"{y['name']}: {y['mech']} " for y in chart["yogas"])
    return {
      "portrait": (f"Лагна — {a['sign_ru']} ({a['nakshatra']}). Душевное ядро (Атмакарака) — "
                   f"{kk['Атмакарака']['pl_ru']}, направление реализации (Каракамса) — {chart['karakamsa']}. "
                   f"Сильнейший инструмент карты — {PL_RU[strongest]} ({vb[strongest]}/20). "
                   f"Богатейшее поле — {best_house}-й дом ({sav[best_house]} бинду), зона роста — "
                   f"{worst_house}-й дом ({sav[worst_house]}). Задайте ANTHROPIC_API_KEY для полного текста."),
      "shodashavarga": f"Рабочий инструмент — {PL_RU[strongest]} ({vb[strongest]}/20). "
                       f"Сильные дома: см. бинду ≥30; уязвимые: <25. (шаблон)",
      "yogas": yoga_txt or "Явных крупных натальных йог не обнаружено. (шаблон)",
      "dasha": (f"Текущая махадаша: {chart['current_dasha']['lord_ru']}. "
                "Полный разбор дуги — при подключённом Claude. (шаблон)"),
      "integral": ("Тип судьбы и формула жизни рассчитываются на основе связки поле×игрок. "
                   "Подключите ANTHROPIC_API_KEY для развёрнутого синтеза. (шаблон)"),
      "planets": "Разбор по каждой планете доступен при подключённом Claude. (шаблон)",
    }


# --------------------------- synastry narrative ---------------------------
_SYN_INSTRUCT = """На основе данных совместимости двух карт напиши JSON строго с ключами
(только JSON, без пояснений):
{
 "intersynastry": "2 абзаца: как планеты одного ложатся на дома другого (особенно 7,5,4,1), что это активирует; тема отношений через Даракараку каждого.",
 "contrasts": "1–2 абзаца: где карты дополняют друг друга (один силён там, где другой слаб), где зеркальная уязвимость (оба слабы), где общая сила (оба сильны — синергия или соперничество).",
 "formula": "1 абзац: тип отношений, главный дар пары и главная точка роста. Тепло, без суждений о людях."
}"""

def _syn_facts(syn: dict) -> str:
    ak = syn["ashtakoota"]
    lines = [f"Аштакута (Гуна Милан): {ak['total']} из 36."]
    lines.append("По кутам: " + ", ".join(f"{r['name']} {r['score']}/{r['max']}" for r in ak["rows"]))
    lines.append(f"Луна {syn['name_a']}: {syn['moon_a']['nak_name']} ({syn['moon_a']['sign_ru']}); "
                 f"Луна {syn['name_b']}: {syn['moon_b']['nak_name']} ({syn['moon_b']['sign_ru']}).")
    lines.append(f"Даракарака {syn['name_a']}: {syn['dara_a']['pl_ru']}; "
                 f"Даракарака {syn['name_b']}: {syn['dara_b']['pl_ru']}.")
    lines.append("Планеты B на ключевых домах A: " +
                 (", ".join(f"{o['planet']}→{o['house']}-й ({o['theme']})" for o in syn["overlay_ab"]) or "нет"))
    lines.append("Планеты A на ключевых домах B: " +
                 (", ".join(f"{o['planet']}→{o['house']}-й ({o['theme']})" for o in syn["overlay_ba"]) or "нет"))
    lines.append(f"Дома-дополнения (один силён, другой слаб): {syn['complements'] or '—'}; "
                 f"зеркальная уязвимость (оба слабы): {syn['mirrors'] or '—'}; "
                 f"общая сила (оба сильны): {syn['shared'] or '—'}.")
    return "\n".join(lines)

def generate_synastry(syn: dict) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        ak = syn["ashtakoota"]
        return {"intersynastry": f"Планеты B на домах A: " +
                    (", ".join(f"{o['planet']}→{o['house']}-й" for o in syn['overlay_ab']) or "нет") +
                    ". Подключите ANTHROPIC_API_KEY для развёрнутого разбора. (шаблон)",
                "contrasts": f"Дополнения: дома {syn['complements'] or '—'}; зеркальные слабости: {syn['mirrors'] or '—'}. (шаблон)",
                "formula": f"Аштакута {ak['total']}/36. Полная формула пары — при подключённом Claude. (шаблон)"}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(model=MODEL, max_tokens=2500, system=SYSTEM,
                                      messages=[{"role":"user","content": _syn_facts(syn) + "\n\n" + _SYN_INSTRUCT}])
        text = "".join(b.text for b in msg.content if getattr(b,"type",None)=="text")
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        out = generate_synastry.__wrapped__(syn) if hasattr(generate_synastry,"__wrapped__") else {
            "intersynastry":"(шаблон)","contrasts":"(шаблон)","formula":f"Аштакута {syn['ashtakoota']['total']}/36."}
        out["_note"] = f"Claude недоступен ({e}); показан шаблон."
        return out
