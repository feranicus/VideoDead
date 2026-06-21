# Multi-stage, non-root, slim. ffmpeg is needed by yt-dlp for muxing.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg nodejs curl unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Always grab the newest yt-dlp at build time (sites change constantly).
RUN pip install --no-cache-dir -U yt-dlp
# Deno: yt-dlp's recommended JS runtime for YouTube's n-challenge (EJS).
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh && deno --version

COPY app ./app

# Run as an unprivileged user; pre-create writable dirs.
RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /data /downloads \
 && chown -R appuser:appuser /app /data /downloads
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
