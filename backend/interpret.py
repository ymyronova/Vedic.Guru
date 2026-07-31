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
import hashlib, os, json

MODEL = os.environ.get("JYOTISH_MODEL", "claude-sonnet-5")

SYSTEM = """Ты — сервис «Джйотиш-Альманах». Пиши ВСЕГДА на русском, тёплым, точным,
образным языком. Это символический интерпретативный материал — не предсказание,
не медицинское и не психологическое суждение о человеке. Никогда не выдумывай
числовые значения: используй только те факты и числа, что переданы во входных
данных. Не осуждай человека, слабые места описывай как зоны роста. Пиши прозой,
без маркированных списков внутри секций.

ТОН И ФОРМАТ — обязательно для каждого текстового блока:

Пиши для человека, который НИЧЕГО не знает о джйотише. Каждое утверждение
строится в два такта: сначала простая человеческая мысль о жизни, характере
или ситуации — потом, сразу за ней в круглых скобках, тот параметр карты, из
которого она следует, на языке джйотиша.

    Вы добиваетесь своего терпением, а не напором (Козерог-лагна, управитель Сатурн).
    Деньги приходят через собственное дело, а не через оклад (Марс управляет
    11-м домом и стоит в нём же, в своём знаке Скорпион).
    Ближайшие два года — про внешние связи и чужие правила игры (махадаша Раху
    до 2040, антардаша Юпитера до 2027).

Правила:
— Никогда не начинай фразу с термина. Термин всегда в скобках, после мысли.
— Не оставляй утверждение без скобки: у каждого вывода должно быть видимое
  основание из карты. Если основания в данных нет — не пиши утверждение.
— В скобках только то, что действительно передано во входных данных: знак,
  дом, накшатра, махадаша/антардаша, бинду, Вимшопака-балл, йога, караки.
— Термины в скобках НЕ переводи и не упрощай — они нужны, чтобы человек мог
  сверить фразу с таблицами отчёта.
— Одна скобка на мысль. Не собирай гирлянды из пяти терминов подряд."""

# Движок хранит достоинство одно-двухбуквенным кодом. Передавать коды модели
# оказалось плохой идеей: в альманахе Анны Солнце описано как «в собственном
# достоинстве», хотя в скобке стоит «достоинство д» — то есть дружественный знак,
# а не свой. Формат «мысль + параметр в скобках» этот разрыв и обнажил. Пишем
# словами, чтобы читать было нечего.
DIGNITY_RU = {
    "Э":  "экзальтация",
    "МТ": "мулатрикона",
    "С":  "свой знак",
    "дд": "великий друг",
    "д":  "дружественный знак",
    "н":  "нейтральный знак",
    "в":  "враждебный знак",
    "вв": "великий враг",
    "П":  "падение",
}

# Входит в отпечаток промпта. Меняете формат фактов — поднимите версию, иначе
# уже сохранённый текст, написанный по старым формулировкам, останется в кэше.
FACTS_VERSION = "2-dignity-words"


def _facts(chart: dict) -> str:
    a = chart["ascendant"]
    lines = [f"Лагна: {a['sign_ru']} {a['dms']}, накшатра {a['nakshatra']} пада {a['pada']}."]
    lines.append("Планеты (знак, дом, дом.№, накшатра, достоинство D1, ретро):")
    for k, pl in chart["planets"].items():
        dg = pl['dignity']
        lines.append(f"  {pl['name']}: {pl['sign_ru']} {pl['dms']}, дом {pl['house']}, "
                     f"накшатра {pl['nakshatra']}, "
                     f"достоинство — {DIGNITY_RU.get(dg, dg)} ({dg})"
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
}

Напоминание про тон: в каждом разделе каждая мысль сначала простыми словами,
и только потом в круглых скобках — джйотиш-параметр, из которого она следует.
Читатель не знает ни одного термина; скобка — его способ сверить фразу с
таблицами отчёта."""

# ─── фокус разбора ────────────────────────────────────────────────────────────
FOCUS_LABELS = {
    "general": "Общий разбор",
    "career":  "Бизнес и карьера",
    "money":   "Деньги и ресурсы",
    "love":    "Любовь и отношения",
}
FOCUS_KEYS = tuple(FOCUS_LABELS) + ("other",)

def focus_label(focus: str | None, note: str = "") -> str:
    """Человеческое название фокуса — оно же попадает в шапку отчёта."""
    if focus == "other":
        return (note or "").strip()[:80] or FOCUS_LABELS["general"]
    return FOCUS_LABELS.get(focus or "general", FOCUS_LABELS["general"])

def _focus_block(focus: str | None, note: str = "") -> str:
    """Инструкция, разворачивающая ВЕСЬ текст в сторону интереса читателя."""
    if not focus or focus == "general":
        return ""
    label = focus_label(focus, note)
    return f"""

ФОКУС РАЗБОРА: {label}

Это не отдельный раздел и не приписка в конце — это призма для всего текста.
Каждый раздел пишется под этот вопрос:
— из каждой конфигурации бери то следствие, которое относится к фокусу, а не
  первое попавшееся;
— примеры и сцены — из этой сферы жизни, конкретные, а не абстрактные;
— рекомендации отвечают на «что мне с этим делать» именно здесь;
— остальные сферы не исчезают, но идут фоном и коротко.

Важное ограничение: НЕ подгоняй карту под фокус. Расчётные факты те же самые —
меняется отбор и объяснение, а не данные. Если по теме фокуса карта ничего
внятного не говорит, так и напиши: это честный ответ, а выдуманная связка —
нет."""


def prompt_fingerprint() -> str:
    """Отпечаток всего, что формирует текст: промпты, инструкции и модель.

    Входит в ключ кэша. Поэтому правка тона или инструкций автоматически
    обесценивает уже сохранённый текст: ключ становится другим, старая запись
    больше не находится, и альманах переписывается под новый промпт. Сбрасывать
    кэш вручную не нужно — иначе правка тона не дошла бы до тех, у кого текст
    уже создан.

    FACTS_VERSION учитывается тоже: модель видит не только промпт, но и блок
    фактов из карты. Правка формулировок в _facts() (например, замена кода
    достоинства на слово) меняет то, что читает модель, — значит старый текст
    тоже должен переписаться, иначе ошибка останется в кэше.

    Уровень усилия (JYOTISH_EFFORT) сюда НЕ входит: это регулятор стоимости, а
    не инструкция. Понижение effort ради экономии не должно выбрасывать уже
    написанные тексты.
    """
    basis = "\n".join([SYSTEM, _INSTRUCT, _SYN_INSTRUCT, MODEL, FACTS_VERSION])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


ALMANAC_KEYS = ("portrait", "shodashavarga", "yogas", "dasha", "integral", "planets")

# Structured outputs: the response is constrained to this schema, so it cannot
# come back as prose, as a code-fenced block, or as JSON with an extra key.
# Previously the model was merely *asked* for JSON and the text was hand-parsed
# after stripping ``` fences — any deviation raised and fell back to a template.
_ALMANAC_SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "string"} for k in ALMANAC_KEYS},
    "required": list(ALMANAC_KEYS),
    "additionalProperties": False,
}

# max_tokens caps thinking AND response text together. Six multi-paragraph
# sections shared a 4000-token budget with adaptive thinking — which the model
# turns on by default when `thinking` is omitted — so the JSON was truncated
# mid-string and every almanac silently fell back to the template.
NARRATIVE_MAX_TOKENS = int(os.environ.get("JYOTISH_MAX_TOKENS", "16000"))
EFFORT = os.environ.get("JYOTISH_EFFORT", "medium")


class NarrativeError(RuntimeError):
    """Claude ran but did not return usable text — kept distinct from auth failures."""


def _looks_like_unsupported_param(e: Exception) -> bool:
    """True when the configured model rejects a modern request field.

    JYOTISH_MODEL is operator-configurable, so someone may point it at a model
    without structured outputs or adaptive thinking. Retry plainly rather than
    dropping to a template.
    """
    m = str(e).lower()
    return any(t in m for t in ("output_config", "output_format", "thinking",
                                "json_schema", "effort", "unexpected keyword"))


def _ask(client, prompt: str, max_tokens: int, schema: dict | None = None):
    """One streamed request. Streaming keeps long generations off the HTTP timeout."""
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=SYSTEM,
                  messages=[{"role": "user", "content": prompt}])
    oc: dict = {"effort": EFFORT}
    if schema is not None:
        oc["format"] = {"type": "json_schema", "schema": schema}
    try:
        with client.messages.stream(thinking={"type": "adaptive"},
                                    output_config=oc, **kwargs) as s:
            return s.get_final_message(), True
    except Exception as e:
        if not _looks_like_unsupported_param(e):
            raise
        with client.messages.stream(**kwargs) as s:      # bare, older-model path
            return s.get_final_message(), False


def _text_of(msg) -> str:
    if getattr(msg, "stop_reason", None) == "refusal":
        raise NarrativeError("модель отклонила запрос (stop_reason=refusal)")
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    if getattr(msg, "stop_reason", None) == "max_tokens":
        # Distinguish "ran out of room" from "could not reach Claude" — the old
        # code reported both as «Claude недоступен».
        raise NarrativeError(
            f"ответ обрезан по max_tokens ({NARRATIVE_MAX_TOKENS}); "
            f"поднимите JYOTISH_MAX_TOKENS или понизьте JYOTISH_EFFORT")
    if not text.strip():
        raise NarrativeError("пустой ответ модели")
    return text


def generate_almanac(chart: dict, focus: str | None = None,
                     focus_note: str = "") -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _fallback(chart)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        prompt = _facts(chart) + "\n\n" + _INSTRUCT + _focus_block(focus, focus_note)
        msg, structured = _ask(client, prompt,
                               NARRATIVE_MAX_TOKENS, _ALMANAC_SCHEMA)
        text = _text_of(msg)
        if not structured:      # older model: still tolerate a fenced block
            text = text.strip().removeprefix("```json").removeprefix("```") \
                       .removesuffix("```").strip()
        data = json.loads(text)
        missing = [k for k in ALMANAC_KEYS if not str(data.get(k, "")).strip()]
        if missing:
            raise NarrativeError(f"в ответе нет разделов: {', '.join(missing)}")
        return data
    except Exception as e:
        out = _fallback(chart)
        out["_note"] = f"Claude недоступен ({type(e).__name__}: {e}); показан шаблон."
        return out

# ─── вопросы к альманаху ──────────────────────────────────────────────────────
ANSWER_MAX_TOKENS = int(os.environ.get("JYOTISH_ANSWER_TOKENS", "4000"))

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

_ANSWER_INSTRUCT = """Ответь на вопрос человека о его карте.

Правила ответа:
— Только факты из переданного расчёта. Никаких новых чисел, знаков, домов и
  периодов: если для ответа нужны данные, которых в расчёте нет, скажи прямо,
  что этого в расчёте нет.
— Тон тот же, что и в альманахе: сначала простая человеческая мысль, потом в
  круглых скобках джйотиш-параметр, из которого она следует.
— Если вопрос вообще не про карту (например, про сервис или про то, как читать
  отчёт) — просто ответь по-человечески, скобки тогда не нужны.
— Если вопрос просит предсказать событие или принять решение за человека,
  ответь тем, что карта показывает как склонность и время, и верни решение
  человеку. Это не предсказание.
— Коротко: 1–3 абзаца. Человек уже прочитал альманах, повторять его не нужно."""


def answer_question(chart: dict, question: str, history: list | None = None,
                    focus: str | None = None, focus_note: str = "",
                    narrative: dict | None = None) -> dict:
    """Ответ на вопрос о карте, опирающийся на тот же расчёт, что и альманах."""
    q = (question or "").strip()
    if not q:
        return {"_template": True, "answer": "Вопрос пустой."}
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"_template": True,
                "answer": "Ответы на вопросы работают при подключённом Claude. "
                          + _why_template()}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)

        parts = [_facts(chart)]
        if narrative:
            # Answers should extend the report, not contradict it, so the model
            # sees what it already said rather than re-deriving from scratch.
            told = "\n\n".join(f"[{k}] {str(narrative.get(k, ''))[:1200]}"
                               for k in ALMANAC_KEYS if narrative.get(k))
            if told:
                parts.append("УЖЕ НАПИСАНО В АЛЬМАНАХЕ (не повторяй, опирайся):\n" + told)
        for turn in (history or [])[-6:]:      # keep the thread, bound the prompt
            qq = str(turn.get("q", ""))[:500]
            aa = str(turn.get("a", ""))[:1500]
            if qq and aa:
                parts.append(f"РАНЕЕ СПРОСИЛИ: {qq}\nВЫ ОТВЕТИЛИ: {aa}")
        parts.append(_ANSWER_INSTRUCT + _focus_block(focus, focus_note))
        parts.append("ВОПРОС: " + q[:1000])

        msg, structured = _ask(client, "\n\n".join(parts),
                               ANSWER_MAX_TOKENS, _ANSWER_SCHEMA)
        text = _text_of(msg)
        if not structured:
            text = text.strip().removeprefix("```json").removeprefix("```") \
                       .removesuffix("```").strip()
        data = json.loads(text)
        if not str(data.get("answer", "")).strip():
            raise NarrativeError("пустой ответ")
        return {"answer": data["answer"]}
    except Exception as e:
        return {"_template": True,
                "answer": f"Не удалось получить ответ ({type(e).__name__}: {e})."}


def rectify_description(chart: dict) -> dict:
    """Step-1 lagna description + two neighbours. Uses Claude if available, else template."""
    a = chart["ascendant"]; key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"_template": True,
                "main": f"Восходящий знак — {a['sign_ru']} ({a['dms']}), накшатра {a['nakshatra']}. "
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
        # 1500 was not enough once thinking started sharing the budget.
        msg, _ = _ask(client, prompt, int(os.environ.get("JYOTISH_LAGNA_TOKENS", "6000")))
        return {"main": _text_of(msg), "confirm": "Узнаёте ли вы себя в этом описании?"}
    except Exception as e:
        return {"_template": True,
                "main": f"Восходящий знак — {a['sign_ru']} {a['dms']}. "
                        f"(Claude недоступен: {type(e).__name__}: {e})",
                "confirm": "Узнаёте ли вы себя в этом знаке?"}

# --------------------------- key liveness probe ---------------------------
# `bool(os.environ.get("ANTHROPIC_API_KEY"))` only says the variable is non-empty.
# An expired key, a revoked key, an empty balance and a wrong model ID all look
# identical to it — and the template fallback then tells the user to "set the key"
# even though the key is set. This makes one cheap call and names the real cause.
PROBE_LABELS = {
    "ok":           "ключ работает",
    "missing":      "ANTHROPIC_API_KEY не задан",
    "invalid_key":  "ключ отклонён (неверный, отозванный или с лишним символом)",
    "no_credit":    "недостаточно средств на балансе Anthropic",
    "no_access":    "у ключа нет доступа к этой модели",
    "bad_model":    "неизвестная модель — проверьте JYOTISH_MODEL",
    "rate_limited": "превышен лимит запросов",
    "unreachable":  "не удалось связаться с API",
    "error":        "неизвестная ошибка",
}

def probe_key(timeout: float = 10.0) -> dict:
    """One minimal request to find out whether the configured key actually works."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"status": "missing", "model": MODEL, "detail": None}
    if key != key.strip():
        # A trailing newline or space from a copy-paste is rejected as a bad key;
        # say so precisely instead of leaving the user to guess.
        return {"status": "invalid_key", "model": MODEL,
                "detail": "ключ содержит пробел или перевод строки по краям"}
    try:
        import anthropic
    except Exception as e:
        return {"status": "error", "model": MODEL, "detail": f"SDK не установлен: {e}"}

    try:
        client = anthropic.Anthropic(api_key=key, timeout=timeout, max_retries=0)
        client.messages.create(model=MODEL, max_tokens=1,
                               messages=[{"role": "user", "content": "ok"}])
        return {"status": "ok", "model": MODEL, "detail": None}
    except anthropic.AuthenticationError as e:
        return {"status": "invalid_key", "model": MODEL, "detail": str(e)[:300]}
    except anthropic.PermissionDeniedError as e:
        return {"status": "no_access", "model": MODEL, "detail": str(e)[:300]}
    except anthropic.NotFoundError as e:
        return {"status": "bad_model", "model": MODEL, "detail": str(e)[:300]}
    except anthropic.RateLimitError as e:
        return {"status": "rate_limited", "model": MODEL, "detail": str(e)[:300]}
    except anthropic.BadRequestError as e:
        msg = str(e)
        low = msg.lower()
        # Anthropic reports an exhausted balance as a 400, not a 402.
        st = "no_credit" if ("credit" in low or "balance" in low) else "error"
        return {"status": st, "model": MODEL, "detail": msg[:300]}
    except anthropic.APIConnectionError as e:
        return {"status": "unreachable", "model": MODEL, "detail": str(e)[:300]}
    except Exception as e:
        return {"status": "error", "model": MODEL, "detail": f"{type(e).__name__}: {e}"[:300]}


# --------------------------- template fallback ---------------------------
def _why_template() -> str:
    """Why the template is showing. 'Set the key' is wrong when the key IS set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "Задайте ANTHROPIC_API_KEY для полного текста."
    return ("Ключ задан, но обращение к Claude не прошло — "
            "причина указана в подвале страницы и в /api/ai.")

def _fallback(chart: dict) -> dict:
    vb = chart["vb"]; strongest = max(vb, key=vb.get)
    from jyotish import PL_RU
    sav = chart["sav_house"]
    best_house = max(sav, key=sav.get); worst_house = min(sav, key=sav.get)
    a = chart["ascendant"]; kk = chart["karakas"]
    yoga_txt = " ".join(f"{y['name']}: {y['mech']} " for y in chart["yogas"])
    return {
      # Marks this as template output. The cache checks it: without an explicit
      # flag, the no-key path returns a fallback carrying no _note, which the
      # cache happily stored — freezing the template in place even after the key
      # was fixed.
      "_template": True,
      "portrait": (f"Лагна — {a['sign_ru']} ({a['nakshatra']}). Душевное ядро (Атмакарака) — "
                   f"{kk['Атмакарака']['pl_ru']}, направление реализации (Каракамса) — {chart['karakamsa']}. "
                   f"Сильнейший инструмент карты — {PL_RU[strongest]} ({vb[strongest]}/20). "
                   f"Богатейшее поле — {best_house}-й дом ({sav[best_house]} бинду), зона роста — "
                   f"{worst_house}-й дом ({sav[worst_house]}). " + _why_template()),
      "shodashavarga": f"Рабочий инструмент — {PL_RU[strongest]} ({vb[strongest]}/20). "
                       f"Сильные дома: см. бинду ≥30; уязвимые: <25. (шаблон)",
      "yogas": yoga_txt or "Явных крупных натальных йог не обнаружено. (шаблон)",
      "dasha": (f"Текущая махадаша: {chart['current_dasha']['lord_ru']}. "
                "Полный разбор дуги — при подключённом Claude. (шаблон)"),
      "integral": ("Тип судьбы и формула жизни рассчитываются на основе связки поле×игрок. "
                   + _why_template() + " (шаблон)"),
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

SYN_KEYS = ("intersynastry", "contrasts", "formula")
_SYN_SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "string"} for k in SYN_KEYS},
    "required": list(SYN_KEYS),
    "additionalProperties": False,
}

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
        return {"_template": True,
                "intersynastry": f"Планеты B на домах A: " +
                    (", ".join(f"{o['planet']}→{o['house']}-й" for o in syn['overlay_ab']) or "нет") +
                    ". Подключите ANTHROPIC_API_KEY для развёрнутого разбора. (шаблон)",
                "contrasts": f"Дополнения: дома {syn['complements'] or '—'}; зеркальные слабости: {syn['mirrors'] or '—'}. (шаблон)",
                "formula": f"Аштакута {ak['total']}/36. Полная формула пары — при подключённом Claude. (шаблон)"}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg, structured = _ask(client, _syn_facts(syn) + "\n\n" + _SYN_INSTRUCT,
                               NARRATIVE_MAX_TOKENS, _SYN_SCHEMA)
        text = _text_of(msg)
        if not structured:
            text = text.strip().removeprefix("```json").removeprefix("```") \
                       .removesuffix("```").strip()
        data = json.loads(text)
        missing = [k for k in SYN_KEYS if not str(data.get(k, "")).strip()]
        if missing:
            raise NarrativeError(f"в ответе нет разделов: {', '.join(missing)}")
        return data
    except Exception as e:
        ak = syn["ashtakoota"]
        # The old handler called generate_synastry.__wrapped__, which never
        # exists — so the fallback itself raised AttributeError on any failure.
        out = {
            "_template": True,
            "intersynastry": "Планеты B на домах A: " +
                (", ".join(f"{o['planet']}→{o['house']}-й" for o in syn['overlay_ab']) or "нет")
                + ". (шаблон)",
            "contrasts": f"Дополнения: дома {syn['complements'] or '—'}; "
                         f"зеркальные слабости: {syn['mirrors'] or '—'}. (шаблон)",
            "formula": f"Аштакута {ak['total']}/36. (шаблон)",
        }
        out["_note"] = f"Claude недоступен ({type(e).__name__}: {e}); показан шаблон."
        return out
