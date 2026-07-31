# ---- Джйотиш-Альманах : production image ----
# One self-contained container that runs the whole service.

FROM python:3.12-slim

# System build tools (needed to compile a couple of the astronomy libraries),
# installed then kept minimal. tzdata gives correct historical timezones.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc build-essential tzdata \
    # WeasyPrint (серверная сборка PDF): Pango рисует текст, остальное — его
    # зависимости и разбор растровых картинок.
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    libffi8 libjpeg62-turbo libopenjp2-7 shared-mime-info \
    # Шрифты ОБЯЗАТЕЛЬНЫ: CSS просит 'DejaVu Serif' и 'FreeSerif'. Без них
    # кириллица в PDF выйдет квадратами — контейнеру неоткуда их взять.
    fonts-dejavu-core fonts-freefont-ttf \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# App code. evals/ is required at runtime: backend/verify.py gates every
# narrative on it, so it ships in the image — not just a dev-time test asset.
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY evals/ ./evals/

# The server reads PORT from the environment (hosts like Render set it).
ENV PORT=8000
EXPOSE 8000
WORKDIR /app/backend

# Shell form so ${PORT} expands at runtime.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
