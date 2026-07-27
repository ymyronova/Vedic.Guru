# ---- Джйотиш-Альманах : production image ----
# One self-contained container that runs the whole service.

FROM python:3.12-slim

# System build tools (needed to compile a couple of the astronomy libraries),
# installed then kept minimal. tzdata gives correct historical timezones.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc build-essential tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# App code.
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# The server reads PORT from the environment (hosts like Render set it).
ENV PORT=8000
EXPOSE 8000
WORKDIR /app/backend

# Shell form so ${PORT} expands at runtime.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
