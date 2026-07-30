# -*- coding: utf-8 -*-
"""
Кэш нарратива по данным рождения.

Зачем: генерация текста альманаха занимает ~70 секунд и стоит токенов. Для одного
и того же человека с теми же данными результат не меняется, поэтому второй запрос
не должен ничего пересчитывать.

Что кэшируется — и что НЕТ
──────────────────────────
Кэшируется только НАРРАТИВ (ответ модели). Расчёт карты, верификация и сборка
HTML выполняются заново на каждый запрос. Это сознательно:

  • расчёт и верификация занимают миллисекунды — экономить там нечего, а гейт
    «расчёт → верификация → нарратив» должен срабатывать всегда, а не один раз;
  • вёрстка меняется чаще текста: закэшируй готовый HTML — и правка дизайна
    не дойдёт до людей, у которых альманах уже создан.

Ключ
────
Не только имя и дата. Ключ — все данные, от которых зависит карта: дата, время,
широта, долгота, часовой пояс (+ имя, оно попадает в текст). Иначе ломается
ректификация: пользователь подбирает время 11:20, потом уточняет на 10:45 — при
ключе «имя + дата» он получил бы старый альманах для 11:20 и не понял, почему
уточнение ни на что не влияет. Один и тот же человек с теми же данными даёт
одинаковый ключ — то есть именно то, что и требовалось.

Хранение
────────
Память процесса + файлы в JYOTISH_CACHE_DIR. На бесплатном тарифе Render диск
эфемерный: кэш живёт, пока живёт инстанс, и теряется при засыпании и деплое.
Внутри одной сессии это уже снимает и ожидание, и повторную оплату токенов. Для
кэша, переживающего перезапуск, нужен постоянный диск или внешнее хранилище —
формат файлов для этого готов, менять код не придётся.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path(os.environ.get("JYOTISH_CACHE_DIR",
                                Path(__file__).resolve().parent.parent / ".cache" / "narrative"))
MEMORY_LIMIT = int(os.environ.get("JYOTISH_CACHE_MEMORY", "64"))
ENABLED = os.environ.get("JYOTISH_CACHE", "1") not in ("0", "false", "False", "no")

_MEM: "dict[str, dict]" = {}
_HITS = _MISSES = _WRITES = 0


def key_for(kind: str, name: str, date: str, time_: str,
            lat: float, lon: float, tz: str) -> str:
    """Stable key over everything the narrative depends on.

    Coordinates are rounded to ~11 m so that a re-geocode of the same city
    (which can wobble in the last decimals) still hits the same entry.
    """
    payload = "|".join([
        kind,
        (name or "").strip().casefold(),
        (date or "").strip(),
        (time_ or "").strip(),
        f"{float(lat):.4f}", f"{float(lon):.4f}",
        (tz or "").strip(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get(key: str) -> dict | None:
    global _HITS, _MISSES
    if not ENABLED:
        return None
    entry = _MEM.get(key)
    if entry is None:
        try:
            with open(_path(key), encoding="utf-8") as f:
                entry = json.load(f)
            _MEM[key] = entry                      # warm memory from disk
        except (OSError, ValueError):
            _MISSES += 1
            return None
    _HITS += 1
    return entry.get("value")


def put(key: str, value: Any) -> None:
    global _WRITES
    if not ENABLED:
        return
    entry = {"key": key, "stored_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "value": value}
    if len(_MEM) >= MEMORY_LIMIT:
        _MEM.pop(next(iter(_MEM)), None)           # simple FIFO trim
    _MEM[key] = entry
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _path(key).with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
        os.replace(tmp, _path(key))                # atomic: no half-written entry
    except OSError:
        pass                                       # memory-only is still useful
    _WRITES += 1


def drop(key: str) -> bool:
    """Forget one entry — used by the force-refresh path."""
    existed = _MEM.pop(key, None) is not None
    try:
        _path(key).unlink()
        existed = True
    except OSError:
        pass
    return existed


def stats() -> dict:
    try:
        on_disk = len(list(CACHE_DIR.glob("*.json")))
    except OSError:
        on_disk = 0
    return {"enabled": ENABLED, "hits": _HITS, "misses": _MISSES, "writes": _WRITES,
            "in_memory": len(_MEM), "on_disk": on_disk, "dir": str(CACHE_DIR),
            "memory_limit": MEMORY_LIMIT,
            "note": "эфемерный на free-тарифе: теряется при засыпании инстанса"}
