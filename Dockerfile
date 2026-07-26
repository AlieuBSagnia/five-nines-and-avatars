# syntax=docker/dockerfile:1

# ---- Build stage: resolve dependencies into a venv we can copy verbatim ----
FROM python:3.12-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage: minimal image, no compilers/build tools ----
FROM python:3.12-slim AS runtime

# Security: run as a non-root, unprivileged user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/false --create-home appuser

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=2)" || exit 1

# uvicorn directly (no reload) — a production ASGI server like gunicorn+uvicorn
# workers would be the next step for multi-core hosts; see README.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
