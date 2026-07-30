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
Не только имя и дата. Ключ — всё, от чего зависит карта: дата, время, широта,
долгота, часовой пояс (+ имя, оно попадает в текст) — И ОТПЕЧАТОК ПРОМПТА
(interpret.prompt_fingerprint()). Иначе:

  • при ключе «имя + дата» ломается ректификация: пользователь подбирает время
    11:20, потом уточняет на 10:45 — и получает старый альманах для 11:20;
  • без отпечатка промпта правка тона не доходит до тех, у кого текст уже есть.
    Меняете SYSTEM или инструкции — отпечаток меняется, старые записи просто
    перестают находиться и текст переписывается под новый промпт. Вручную ничего
    сбрасывать не нужно.

Где хранится
────────────
Два бэкенда, выбор автоматический:

  DATABASE_URL задан  → PostgreSQL. Переживает засыпание инстанса и деплой.
                         Годится бесплатный тариф Neon или Supabase.
  DATABASE_URL пуст   → файлы в JYOTISH_CACHE_DIR + память процесса.
                         На free-тарифе Render диск эфемерный: кэш живёт, пока
                         живёт контейнер, и теряется при засыпании (~15 минут
                         простоя) и при каждом деплое.

Любая ошибка базы не ломает запрос: модуль тихо переходит на файлы и память.
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
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

_MEM: "dict[str, dict]" = {}
_STATS = {"hits": 0, "misses": 0, "writes": 0, "db_errors": 0}
_DB_READY = False
_DB_DISABLED = False          # set after a hard failure, so we stop retrying


# ─── ключ ─────────────────────────────────────────────────────────────────────

def key_for(kind: str, name: str, date: str, time_: str,
            lat: float, lon: float, tz: str, prompt: str = "") -> str:
    """Стабильный ключ по всему, от чего зависит текст.

    Координаты округляются до ~11 м, чтобы повторное геокодирование того же
    города (последние знаки могут дрожать) попадало в ту же запись.
    """
    payload = "|".join([
        kind,
        (name or "").strip().casefold(),
        (date or "").strip(),
        (time_ or "").strip(),
        f"{float(lat):.4f}", f"{float(lon):.4f}",
        (tz or "").strip(),
        (prompt or "").strip(),          # отпечаток промпта
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


# ─── PostgreSQL ───────────────────────────────────────────────────────────────

def _db():
    """Соединение или None. Таблица создаётся при первом обращении."""
    global _DB_READY, _DB_DISABLED
    if not DATABASE_URL or _DB_DISABLED:
        return None
    try:
        import psycopg
    except Exception:
        _DB_DISABLED = True             # драйвер не установлен — работаем на файлах
        return None
    try:
        conn = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=10)
    except Exception:
        _STATS["db_errors"] += 1
        return None
    if not _DB_READY:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS narrative_cache (
                        key       TEXT PRIMARY KEY,
                        stored_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        value     JSONB NOT NULL
                    )
                """)
            _DB_READY = True
        except Exception:
            _STATS["db_errors"] += 1
            conn.close()
            return None
    return conn


def _db_get(key: str):
    conn = _db()
    if conn is None:
        return None
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT value FROM narrative_cache WHERE key = %s", (key,))
            row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        _STATS["db_errors"] += 1
        return None
    finally:
        conn.close()


def _db_put(key: str, value: Any) -> bool:
    conn = _db()
    if conn is None:
        return False
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO narrative_cache (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, stored_at = now()
            """, (key, json.dumps(value, ensure_ascii=False)))
        return True
    except Exception:
        _STATS["db_errors"] += 1
        return False
    finally:
        conn.close()


def _db_drop(key: str) -> bool:
    conn = _db()
    if conn is None:
        return False
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM narrative_cache WHERE key = %s", (key,))
            return cur.rowcount > 0
    except Exception:
        _STATS["db_errors"] += 1
        return False
    finally:
        conn.close()


def _db_count() -> int | None:
    conn = _db()
    if conn is None:
        return None
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM narrative_cache")
            return cur.fetchone()[0]
    except Exception:
        _STATS["db_errors"] += 1
        return None
    finally:
        conn.close()


# ─── файлы ────────────────────────────────────────────────────────────────────

def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _file_get(key: str):
    try:
        with open(_path(key), encoding="utf-8") as f:
            return json.load(f).get("value")
    except (OSError, ValueError):
        return None


def _file_put(key: str, value: Any) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _path(key).with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"key": key,
                       "stored_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "value": value}, f, ensure_ascii=False)
        os.replace(tmp, _path(key))          # атомарно: нет полузаписанных файлов
    except OSError:
        pass                                 # памяти процесса всё равно достаточно


# ─── публичный интерфейс ──────────────────────────────────────────────────────

def get(key: str) -> dict | None:
    if not ENABLED:
        return None
    value = _MEM.get(key)
    if value is None:
        value = _db_get(key)
    if value is None:
        value = _file_get(key)
    if value is None:
        _STATS["misses"] += 1
        return None
    _MEM[key] = value                        # прогреваем память
    _STATS["hits"] += 1
    return value


def put(key: str, value: Any) -> None:
    if not ENABLED:
        return
    if len(_MEM) >= MEMORY_LIMIT:
        _MEM.pop(next(iter(_MEM)), None)     # простое FIFO-подрезание
    _MEM[key] = value
    if not _db_put(key, value):
        _file_put(key, value)                # база недоступна — пишем в файл
    _STATS["writes"] += 1


def drop(key: str) -> bool:
    existed = _MEM.pop(key, None) is not None
    if _db_drop(key):
        existed = True
    try:
        _path(key).unlink()
        existed = True
    except OSError:
        pass
    return existed


def backend() -> str:
    if not DATABASE_URL:
        return "files"
    if _DB_DISABLED:
        return "files (нет драйвера psycopg)"
    return "postgres" if _db_count() is not None else "files (база недоступна)"


def stats() -> dict:
    try:
        on_disk = len(list(CACHE_DIR.glob("*.json")))
    except OSError:
        on_disk = 0
    kind = backend()
    return {
        "enabled": ENABLED,
        "backend": kind,
        "persistent": kind == "postgres",
        **_STATS,
        "in_memory": len(_MEM),
        "on_disk": on_disk,
        "in_db": _db_count(),
        "dir": str(CACHE_DIR),
        "memory_limit": MEMORY_LIMIT,
        "note": ("постоянный: переживает засыпание и деплой" if kind == "postgres"
                 else "эфемерный на free-тарифе: теряется при засыпании инстанса; "
                      "задайте DATABASE_URL для постоянного кэша"),
    }
