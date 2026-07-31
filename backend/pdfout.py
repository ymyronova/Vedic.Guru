# -*- coding: utf-8 -*-
"""
Сборка PDF из готового HTML альманаха.

Движок — WeasyPrint. Не headless Chromium: тот требует 300–500 МБ при рендере и
не помещается в 512 МБ бесплатного тарифа рядом с индексом городов; падение по
памяти уронило бы весь сервис, а не только скачивание.

Безопасность
────────────
На вход приходит HTML, собранный этим же сервисом, но приходит он от клиента.
Поэтому все внешние загрузки запрещены жёстко: url_fetcher отклоняет любой URL.
Это закрывает и SSRF (запрос к внутренней сети через <img src>), и чтение
локальных файлов (file:///etc/passwd), и заодно делает рендер детерминированным.

Ограничение честное: наш альманах самодостаточен — стили инлайн, диаграммы
инлайновый SVG, шрифты системные, — поэтому запрещать нечего, ничего не ломается.

Шрифты
──────
Кириллица требует шрифтов В ОБРАЗЕ. CSS просит 'DejaVu Serif' и 'FreeSerif';
Dockerfile ставит fonts-dejavu-core и fonts-freefont-ttf. Без них текст выйдет
квадратами — это первое, что нужно проверить на новом окружении.
"""
from __future__ import annotations

import re

MAX_HTML_BYTES = 4_000_000          # ~4 МБ: альманах весит ~60 КБ


class PdfUnavailable(RuntimeError):
    """Движок не установлен или не смог инициализироваться."""


def _blocked_fetcher(url: str, *args, **kwargs):
    raise ValueError(f"внешние ресурсы запрещены при сборке PDF: {url[:120]}")


def available() -> tuple[bool, str]:
    """(доступен, причина). Импорт ленивый: без системных библиотек он падает."""
    try:
        import weasyprint
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    return True, getattr(weasyprint, "__version__", "?")


def html_to_pdf(html: str) -> bytes:
    if not isinstance(html, str) or not html.strip():
        raise ValueError("пустой HTML")
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("документ слишком большой")
    try:
        from weasyprint import HTML
    except Exception as e:
        raise PdfUnavailable(f"{type(e).__name__}: {e}") from e
    return HTML(string=html, url_fetcher=_blocked_fetcher).write_pdf()


_SAFE = re.compile(r"[^\w\-. ]+", re.UNICODE)

def safe_filename(name: str, fallback: str = "almanac") -> str:
    """Имя файла без путей и управляющих символов; кириллицу сохраняем."""
    base = _SAFE.sub("", (name or "").strip()).strip(" .")
    base = re.sub(r"\s+", "_", base)
    return (base or fallback)[:80]
